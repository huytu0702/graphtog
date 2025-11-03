"""
Entity Resolution Service for GraphRAG
Handles entity deduplication, disambiguation, and merging using fuzzy matching and LLM
"""

import hashlib
import logging
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai

from app.config import get_settings
from app.services.graph_service import graph_service

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure Gemini if API key is provided
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)


class EntityResolutionService:
    """Service for entity resolution, deduplication, and disambiguation"""

    def __init__(self, similarity_threshold: float = 0.85):
        """
        Initialize entity resolution service

        Args:
            similarity_threshold: Minimum similarity score (0.0-1.0) for fuzzy matching
        """
        self.similarity_threshold = similarity_threshold
        self.model_name = "gemini-2.5-flash-lite"

    def calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate similarity between two strings using SequenceMatcher

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score between 0.0 and 1.0
        """
        # Normalize strings for comparison
        s1 = str1.lower().strip()
        s2 = str2.lower().strip()

        # Exact match
        if s1 == s2:
            return 1.0

        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, s1, s2).ratio()

    def find_similar_entities(
        self,
        entity_name: str,
        entity_type: str,
        threshold: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find similar entities in the graph using fuzzy matching

        Args:
            entity_name: Entity name to search for
            entity_type: Entity type (PERSON, ORGANIZATION, etc.)
            threshold: Optional custom threshold (uses instance default if not provided)

        Returns:
            List of similar entities with similarity scores
        """
        try:
            session = graph_service.get_session()
            threshold = threshold or self.similarity_threshold

            # Get all entities of the same type
            query = """
            MATCH (e:Entity {type: $entity_type})
            RETURN e.id as id, e.name as name, e.type as type,
                   e.description as description, e.confidence as confidence,
                   e.mention_count as mention_count
            """

            result = session.run(query, entity_type=entity_type)
            candidates = [dict(record) for record in result]

            # Calculate similarities
            similar_entities = []
            for candidate in candidates:
                similarity = self.calculate_similarity(entity_name, candidate["name"])

                if similarity >= threshold and similarity < 1.0:  # Exclude exact matches
                    similar_entities.append({
                        **candidate,
                        "similarity": round(similarity, 3),
                    })

            # Sort by similarity (highest first)
            similar_entities.sort(key=lambda x: x["similarity"], reverse=True)

            logger.info(
                f"Found {len(similar_entities)} similar entities for '{entity_name}' "
                f"(type: {entity_type}, threshold: {threshold})"
            )

            return similar_entities

        except Exception as e:
            logger.error(f"Error finding similar entities: {e}")
            return []

    def find_duplicate_entity_pairs(
        self, entity_type: Optional[str] = None, threshold: Optional[float] = None
    ) -> List[Tuple[Dict[str, Any], Dict[str, Any], float]]:
        """
        Find all potential duplicate entity pairs in the graph

        Args:
            entity_type: Optional filter by entity type
            threshold: Optional custom similarity threshold

        Returns:
            List of tuples (entity1, entity2, similarity_score)
        """
        try:
            session = graph_service.get_session()
            threshold = threshold or self.similarity_threshold

            # Get all entities (optionally filtered by type)
            if entity_type:
                query = """
                MATCH (e:Entity {type: $entity_type})
                RETURN e.id as id, e.name as name, e.type as type,
                       e.description as description, e.confidence as confidence,
                       e.mention_count as mention_count
                ORDER BY e.name
                """
                result = session.run(query, entity_type=entity_type)
            else:
                query = """
                MATCH (e:Entity)
                RETURN e.id as id, e.name as name, e.type as type,
                       e.description as description, e.confidence as confidence,
                       e.mention_count as mention_count
                ORDER BY e.type, e.name
                """
                result = session.run(query)

            entities = [dict(record) for record in result]

            # Find pairs with similarity above threshold
            duplicate_pairs = []
            checked = set()

            for i, entity1 in enumerate(entities):
                for entity2 in entities[i + 1 :]:
                    # Only compare entities of the same type
                    if entity1["type"] != entity2["type"]:
                        continue

                    # Skip if already checked
                    pair_key = tuple(sorted([entity1["id"], entity2["id"]]))
                    if pair_key in checked:
                        continue

                    checked.add(pair_key)

                    similarity = self.calculate_similarity(entity1["name"], entity2["name"])

                    if similarity >= threshold:
                        duplicate_pairs.append((entity1, entity2, round(similarity, 3)))

            # Sort by similarity (highest first)
            duplicate_pairs.sort(key=lambda x: x[2], reverse=True)

            logger.info(
                f"Found {len(duplicate_pairs)} potential duplicate pairs "
                f"(threshold: {threshold})"
            )

            return duplicate_pairs

        except Exception as e:
            logger.error(f"Error finding duplicate pairs: {e}")
            return []

    async def resolve_with_llm(
        self,
        entity1: Dict[str, Any],
        entity2: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Use LLM to determine if two entities are the same

        Args:
            entity1: First entity dict
            entity2: Second entity dict

        Returns:
            Dict with resolution result
        """
        try:
            prompt = f"""You are an expert entity resolution system. Determine if the following two entities refer to the same real-world entity.

Entity 1:
- Name: {entity1['name']}
- Type: {entity1['type']}
- Description: {entity1.get('description', 'N/A')}
- Mention Count: {entity1.get('mention_count', 1)}

Entity 2:
- Name: {entity2['name']}
- Type: {entity2['type']}
- Description: {entity2.get('description', 'N/A')}
- Mention Count: {entity2.get('mention_count', 1)}

Analyze carefully:
1. Are these names referring to the same entity (e.g., "Microsoft" vs "MS", "John Smith" vs "J. Smith")?
2. Do the descriptions suggest they are the same entity?
3. Consider context, abbreviations, nicknames, and common aliases

Respond in JSON format:
{{
  "are_same": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of your decision",
  "suggested_canonical_name": "The best name to use if they are the same"
}}"""

            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            response_text = response.text.strip()

            # Parse JSON response
            import json
            import re

            # Remove markdown code blocks using proper regex
            if "```" in response_text:
                # Extract content between code blocks
                code_block_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
                matches = re.findall(code_block_pattern, response_text, re.DOTALL)
                if matches:
                    response_text = matches[0].strip()
                else:
                    # Fallback: remove all ``` markers
                    response_text = re.sub(r'```[a-z]*\n?', '', response_text).strip()
                    response_text = response_text.replace('```', '').strip()

            # Remove any control characters
            response_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', response_text)

            # Check for empty response
            if not response_text:
                logger.warning("Empty response after cleaning")
                return {
                    "status": "error",
                    "error": "Empty response from LLM",
                    "are_same": False,
                    "confidence": 0.0,
                }

            result = json.loads(response_text.strip())

            logger.info(
                f"LLM resolution: '{entity1['name']}' vs '{entity2['name']}' -> "
                f"{result.get('are_same')} (confidence: {result.get('confidence')})"
            )

            return {
                "status": "success",
                "are_same": result.get("are_same", False),
                "confidence": result.get("confidence", 0.0),
                "reasoning": result.get("reasoning", ""),
                "suggested_canonical_name": result.get("suggested_canonical_name", entity1["name"]),
            }

        except Exception as e:
            logger.error(f"LLM resolution error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "are_same": False,
                "confidence": 0.0,
            }

    def merge_entities(
        self,
        primary_entity_id: str,
        duplicate_entity_ids: List[str],
        canonical_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Merge duplicate entities into a primary entity

        This will:
        1. Aggregate mention counts
        2. Transfer all relationships to primary entity
        3. Transfer all text unit mentions
        4. Store aliases for duplicate names
        5. Delete duplicate entities

        Args:
            primary_entity_id: ID of entity to keep
            duplicate_entity_ids: List of entity IDs to merge into primary
            canonical_name: Optional canonical name to use for merged entity

        Returns:
            Dict with merge result
        """
        try:
            session = graph_service.get_session()

            # Validate that primary entity exists
            primary_check = session.run(
                "MATCH (e:Entity {id: $id}) RETURN e",
                id=primary_entity_id
            )
            if not primary_check.single():
                return {
                    "status": "error",
                    "error": f"Primary entity {primary_entity_id} not found"
                }

            merged_count = 0
            aliases = []

            for dup_id in duplicate_entity_ids:
                # Get duplicate entity info
                dup_result = session.run(
                    """
                    MATCH (dup:Entity {id: $dup_id})
                    RETURN dup.name as name, dup.mention_count as mention_count,
                           dup.description as description
                    """,
                    dup_id=dup_id
                )
                dup_record = dup_result.single()

                if not dup_record:
                    logger.warning(f"Duplicate entity {dup_id} not found, skipping")
                    continue

                dup_data = dict(dup_record)
                aliases.append(dup_data["name"])

                # Merge operation in a single transaction
                merge_query = """
                // Get both entities
                MATCH (primary:Entity {id: $primary_id})
                MATCH (dup:Entity {id: $dup_id})

                // Update primary entity
                SET primary.mention_count = COALESCE(primary.mention_count, 1) + COALESCE(dup.mention_count, 1)
                SET primary.updated_at = datetime()

                // Add alias property if not exists
                SET primary.aliases = CASE
                    WHEN primary.aliases IS NULL THEN [dup.name]
                    WHEN NOT dup.name IN primary.aliases THEN primary.aliases + dup.name
                    ELSE primary.aliases
                END

                // Transfer all MENTIONED_IN relationships
                WITH primary, dup
                MATCH (dup)-[r:MENTIONED_IN]->(t:TextUnit)
                MERGE (primary)-[:MENTIONED_IN]->(t)
                DELETE r

                // Transfer all outgoing relationships (preserving highest confidence)
                WITH primary, dup
                OPTIONAL MATCH (dup)-[r_out]->(target:Entity)
                WHERE type(r_out) <> 'MENTIONED_IN'
                WITH primary, dup, r_out, target, type(r_out) as rel_type
                WHERE target IS NOT NULL AND target.id <> primary.id
                CALL apoc.merge.relationship(
                    primary, rel_type, {},
                    {confidence: COALESCE(r_out.confidence, 0.8), description: r_out.description},
                    target,
                    {confidence: 'GREATEST', updated_at: datetime()}
                ) YIELD rel
                DELETE r_out

                // Transfer all incoming relationships
                WITH primary, dup
                OPTIONAL MATCH (source:Entity)-[r_in]->(dup)
                WHERE type(r_in) <> 'MENTIONED_IN'
                WITH primary, dup, r_in, source, type(r_in) as rel_type
                WHERE source IS NOT NULL AND source.id <> primary.id
                CALL apoc.merge.relationship(
                    source, rel_type, {},
                    {confidence: COALESCE(r_in.confidence, 0.8), description: r_in.description},
                    primary,
                    {confidence: 'GREATEST', updated_at: datetime()}
                ) YIELD rel
                DELETE r_in

                // Delete duplicate entity
                WITH primary, dup
                DETACH DELETE dup

                RETURN primary.id as id, primary.mention_count as mention_count,
                       primary.aliases as aliases
                """

                try:
                    result = session.run(
                        merge_query,
                        primary_id=primary_entity_id,
                        dup_id=dup_id
                    )
                    result.consume()  # Ensure query completes
                    merged_count += 1
                    logger.info(f"Merged entity {dup_id} into {primary_entity_id}")

                except Exception as e:
                    # Handle constraint violation (entity already merged)
                    if "ConstraintValidationFailed" in str(e) or "already exists" in str(e):
                        logger.warning(f"Entity {dup_id} may already be merged or duplicate entity {primary_entity_id} already exists, skipping")
                        # Still count as processed
                        merged_count += 1
                    # If APOC is not available, fall back to simpler merge
                    elif "apoc" in str(e).lower():
                        logger.warning("APOC not available, using simplified merge")
                        self._merge_entities_without_apoc(
                            session, primary_entity_id, dup_id
                        )
                        merged_count += 1
                    else:
                        logger.error(f"Error merging entity {dup_id}: {e}")

            # Update canonical name if provided and different from current name
            if canonical_name:
                # First check if the canonical name is different from the primary entity's current name
                check_query = """
                MATCH (e:Entity {id: $id})
                RETURN e.name as current_name, e.type as entity_type
                """
                check_result = session.run(check_query, id=primary_entity_id).single()

                if check_result and check_result["current_name"] != canonical_name:
                    # Check if an entity with this canonical name already exists (different entity)
                    conflict_check = """
                    MATCH (e:Entity {name: $canonical_name, type: $entity_type})
                    WHERE e.id <> $primary_id
                    RETURN e.id as conflicting_id
                    """
                    conflict = session.run(
                        conflict_check,
                        canonical_name=canonical_name,
                        entity_type=check_result["entity_type"],
                        primary_id=primary_entity_id
                    ).single()

                    if conflict:
                        logger.warning(
                            f"Cannot update canonical name to '{canonical_name}' - "
                            f"another entity already exists with this name (id: {conflict['conflicting_id']})"
                        )
                    else:
                        # Safe to update - no conflict
                        try:
                            session.run(
                                """
                                MATCH (e:Entity {id: $id})
                                SET e.name = $canonical_name, e.updated_at = datetime()
                                """,
                                id=primary_entity_id,
                                canonical_name=canonical_name
                            )
                            logger.info(f"Updated canonical name to '{canonical_name}' for entity {primary_entity_id}")
                        except Exception as e:
                            logger.error(f"Unexpected error updating canonical name: {e}")

            logger.info(
                f"Successfully merged {merged_count} entities into {primary_entity_id}"
            )

            return {
                "status": "success",
                "primary_entity_id": primary_entity_id,
                "merged_count": merged_count,
                "aliases": aliases,
                "canonical_name": canonical_name,
            }

        except Exception as e:
            # Don't log constraint violations as errors - they're handled gracefully
            if "ConstraintValidationFailed" not in str(e) and "already exists" not in str(e):
                logger.error(f"Entity merge error: {e}")
            return {
                "status": "error",
                "error": str(e),
                "merged_count": 0,
            }

    def _merge_entities_without_apoc(
        self, session, primary_id: str, dup_id: str
    ) -> None:
        """
        Fallback merge method without APOC procedures

        Args:
            session: Neo4j session
            primary_id: Primary entity ID
            dup_id: Duplicate entity ID
        """
        # Transfer MENTIONED_IN relationships
        session.run(
            """
            MATCH (dup:Entity {id: $dup_id})-[r:MENTIONED_IN]->(t:TextUnit)
            MATCH (primary:Entity {id: $primary_id})
            MERGE (primary)-[:MENTIONED_IN]->(t)
            DELETE r
            """,
            primary_id=primary_id,
            dup_id=dup_id
        )

        # Update mention count and aliases
        session.run(
            """
            MATCH (primary:Entity {id: $primary_id})
            MATCH (dup:Entity {id: $dup_id})
            SET primary.mention_count = COALESCE(primary.mention_count, 1) + COALESCE(dup.mention_count, 1)
            SET primary.aliases = CASE
                WHEN primary.aliases IS NULL THEN [dup.name]
                WHEN NOT dup.name IN primary.aliases THEN primary.aliases + dup.name
                ELSE primary.aliases
            END
            SET primary.updated_at = datetime()
            """,
            primary_id=primary_id,
            dup_id=dup_id
        )

        # Delete duplicate
        session.run(
            "MATCH (dup:Entity {id: $dup_id}) DETACH DELETE dup",
            dup_id=dup_id
        )

    def get_entity_aliases(self, entity_id: str) -> List[str]:
        """
        Get all known aliases for an entity

        Args:
            entity_id: Entity ID

        Returns:
            List of alias names
        """
        try:
            session = graph_service.get_session()

            result = session.run(
                """
                MATCH (e:Entity {id: $entity_id})
                RETURN e.name as canonical_name, e.aliases as aliases
                """,
                entity_id=entity_id
            )

            record = result.single()
            if not record:
                return []

            aliases = record.get("aliases", []) or []
            canonical_name = record.get("canonical_name", "")

            # Return canonical name + aliases
            return [canonical_name] + aliases

        except Exception as e:
            logger.error(f"Error getting entity aliases: {e}")
            return []

    def add_entity_alias(
        self, entity_id: str, alias: str
    ) -> bool:
        """
        Add an alias to an existing entity

        Args:
            entity_id: Entity ID
            alias: Alias name to add

        Returns:
            True if successful, False otherwise
        """
        try:
            session = graph_service.get_session()

            session.run(
                """
                MATCH (e:Entity {id: $entity_id})
                SET e.aliases = CASE
                    WHEN e.aliases IS NULL THEN [$alias]
                    WHEN NOT $alias IN e.aliases THEN e.aliases + $alias
                    ELSE e.aliases
                END
                SET e.updated_at = datetime()
                """,
                entity_id=entity_id,
                alias=alias
            )

            logger.info(f"Added alias '{alias}' to entity {entity_id}")
            return True

        except Exception as e:
            logger.error(f"Error adding alias: {e}")
            return False


# Export singleton instance
entity_resolution_service = EntityResolutionService()
