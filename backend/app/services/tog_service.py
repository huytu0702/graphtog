"""
Tree of Graphs (ToG) reasoning service for multi-hop knowledge graph traversal.

Implements iterative graph exploration with LLM-guided pruning for complex query answering.
Based on the ToG methodology adapted for GraphRAG knowledge graphs.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from difflib import SequenceMatcher
import re

from app.services.graph_service import GraphService
from app.services.llm_service import LLMService
from app.services.prompt import (
    TOG_TOPIC_ENTITY_EXTRACTION_PROMPT,
    TOG_RELATION_EXTRACTION_PROMPT,
    TOG_ENTITY_SCORING_PROMPT,
    TOG_SUFFICIENCY_CHECK_PROMPT,
    TOG_FINAL_ANSWER_PROMPT,
)

logger = logging.getLogger(__name__)


@dataclass
class ToGConfig:
    """Configuration for ToG reasoning parameters."""

    # Exploration parameters
    search_width: int = 3  # Max entities to explore per depth level
    search_depth: int = 3  # Max traversal depth
    num_retain_entity: int = 5  # Max entities to retain during search

    # LLM temperature settings
    exploration_temp: float = 0.4  # Temperature for exploration phase
    reasoning_temp: float = 0.0  # Temperature for reasoning phase

    # Pruning and evaluation
    pruning_method: str = "llm"  # llm, bm25, or sentence_bert
    enable_sufficiency_check: bool = True

    # Filtering
    document_ids: Optional[List[int]] = None  # Filter to specific documents


@dataclass
class ToGEntity:
    """Represents an entity in the ToG reasoning process."""

    id: str
    name: str
    type: str
    description: Optional[str] = None
    confidence: float = 1.0
    document_id: Optional[int] = None

    def __hash__(self):
        return hash((self.id, self.name))

    def __eq__(self, other):
        if not isinstance(other, ToGEntity):
            return False
        return self.id == other.id and self.name == other.name


@dataclass
class ToGRelation:
    """Represents a relation in the ToG reasoning process."""

    type: str
    source_entity: ToGEntity
    target_entity: ToGEntity
    description: Optional[str] = None
    confidence: float = 1.0
    score: float = 0.0  # LLM-assigned relevance score

    def __hash__(self):
        return hash((self.type, self.source_entity.id, self.target_entity.id))

    def __eq__(self, other):
        if not isinstance(other, ToGRelation):
            return False
        return (
            self.type == other.type
            and self.source_entity.id == other.source_entity.id
            and self.target_entity.id == other.target_entity.id
        )


@dataclass
class ToGReasoningStep:
    """Represents a single step in the ToG reasoning path."""

    depth: int
    entities_explored: List[ToGEntity]
    relations_selected: List[ToGRelation]
    sufficiency_score: Optional[float] = None
    reasoning_notes: Optional[str] = None


@dataclass
class ToGTriplet:
    """Knowledge triplet extracted during ToG reasoning."""

    subject: str
    relation: str
    object: str
    confidence: float = 1.0
    source: Optional[str] = None  # Source of the triplet (e.g., document, step)

    def __hash__(self):
        return hash((self.subject, self.relation, self.object))

    def __eq__(self, other):
        if not isinstance(other, ToGTriplet):
            return False
        return (
            self.subject == other.subject
            and self.relation == other.relation
            and self.object == other.object
        )


@dataclass
class ToGReasoningPath:
    """Complete reasoning path from ToG traversal."""

    steps: List[ToGReasoningStep] = field(default_factory=list)
    final_answer: Optional[str] = None
    confidence_score: float = 0.0
    sufficiency_status: str = "unknown"  # unknown, sufficient, insufficient
    retrieved_triplets: List[ToGTriplet] = field(default_factory=list)


class ToGService:
    """
    Tree of Graphs reasoning service for multi-hop knowledge graph traversal.

    Implements the ToG methodology adapted for GraphRAG:
    1. Extract topic entities from question
    2. Iteratively explore relations and entities with LLM-guided pruning
    3. Evaluate sufficiency and generate final answer
    """

    def __init__(self, graph_service: GraphService, llm_service: LLMService):
        """Initialize ToG service with dependencies."""
        self.graph_service = graph_service
        self.llm_service = llm_service

        # Tracking state during traversal
        self.explored_entities: Set[ToGEntity] = set()
        self.explored_relations: Set[str] = set()  # Track relation types to avoid cycles
        self.reasoning_path: ToGReasoningPath = ToGReasoningPath()
        self.retrieved_triplets: Set[ToGTriplet] = set()  # Track all retrieved triplets

        # Pruning method (initialized per query based on config)
        self.pruning_method = None

    async def process_query(self, question: str, config: ToGConfig) -> ToGReasoningPath:
        """
        Main ToG reasoning entry point with comprehensive error handling.

        Args:
            question: User question to answer
            config: ToG configuration parameters

        Returns:
            Complete reasoning path with answer
        """
        logger.info(f"Starting ToG reasoning for question: {question}")
        return await self.process_query_safe(question, config)

    async def _extract_topic_entities(
        self, question: str, document_ids: Optional[List[int]]
    ) -> List[str]:
        """
        Extract initial topic entities from question.

        Steps:
        1. Get available entities from graph (filtered by documents if specified)
        2. Use LLM to identify entities mentioned in question
        3. Match to actual graph entities (fuzzy matching)
        4. Return ranked list of starting entities
        """
        logger.info(f"Extracting topic entities for: {question}")

        # Get available entities from graph
        available_entities = self._get_available_entities(document_ids)
        logger.debug(f"Found {len(available_entities)} entities in graph")

        # If no entities in graph, return empty
        if not available_entities:
            return []

        # Prepare prompt
        entity_sample = (
            available_entities[:100] if len(available_entities) > 100 else available_entities
        )

        prompt = TOG_TOPIC_ENTITY_EXTRACTION_PROMPT.format(
            question=question, available_entities=", ".join(entity_sample)
        )

        # Call LLM
        response = await self.llm_service.generate_text(
            prompt=prompt, temperature=0.2  # Lower temperature for entity extraction
        )

        # Parse response
        result = self.llm_service._parse_json_response(response)
        topic_entities = result.get("topic_entities", [])

        logger.info(f"LLM extracted topic entities: {topic_entities}")

        # Validate against available entities and fuzzy match if needed
        validated_entities = []
        for entity_name in topic_entities:
            # Direct match
            if entity_name in available_entities:
                validated_entities.append(entity_name)
            else:
                # Fuzzy match
                fuzzy_match = self._fuzzy_match_entity(entity_name, available_entities)
                if fuzzy_match:
                    validated_entities.append(fuzzy_match)

        # If LLM didn't find matches, fall back to fuzzy matching on question
        if not validated_entities:
            validated_entities = self._fuzzy_match_entities_from_question(
                question, available_entities
            )

        logger.info(f"Validated topic entities: {validated_entities}")
        return validated_entities

    def _get_available_entities(self, document_ids: Optional[List[int]]) -> List[str]:
        """Get entity names from graph, optionally filtered by documents."""
        query = """
        MATCH (e:Entity)
        """

        if document_ids:
            query += """
            WHERE e.document_id IN $document_ids
            """

        query += """
        WITH DISTINCT e.name as name, e.mention_count as mention_count
        RETURN name
        ORDER BY mention_count DESC
        LIMIT 1000
        """

        with self.graph_service.get_session() as session:
            result = session.run(query, {"document_ids": document_ids})
            entities = [record["name"] for record in result]
            return entities

    def _fuzzy_match_entity(
        self, target_entity: str, available_entities: List[str]
    ) -> Optional[str]:
        """Fuzzy match a single entity name against available entities."""
        target_lower = target_entity.lower()

        best_match = None
        best_score = 0.0

        for entity in available_entities:
            entity_lower = entity.lower()
            score = SequenceMatcher(None, target_lower, entity_lower).ratio()

            if score > best_score and score > 0.8:  # High threshold for fuzzy matching
                best_score = score
                best_match = entity

        return best_match

    def _fuzzy_match_entities_from_question(
        self, question: str, available_entities: List[str], top_k: int = 3
    ) -> List[str]:
        """Fuzzy match question tokens to entity names."""
        # Tokenize question (simple approach)
        question_lower = question.lower()
        words = re.findall(r"\w+", question_lower)

        # Filter to meaningful words
        meaningful_words = [word for word in words if len(word) > 2]

        # Score each entity
        entity_scores = []
        for entity in available_entities:
            entity_lower = entity.lower()
            max_score = 0.0

            # Check if entity name appears in question
            if entity_lower in question_lower:
                max_score = 1.0
            else:
                # Fuzzy match against question words
                for word in meaningful_words:
                    score = SequenceMatcher(None, word, entity_lower).ratio()
                    max_score = max(max_score, score)

            if max_score > 0.6:  # Threshold
                entity_scores.append((entity, max_score))

        # Sort and return top-k
        entity_scores.sort(key=lambda x: x[1], reverse=True)
        matched = [entity for entity, score in entity_scores[:top_k]]

        logger.info(f"Fuzzy matched entities from question: {matched}")
        return matched

    def _get_entity_by_name(
        self, entity_name: str, document_ids: Optional[List[int]]
    ) -> Optional[ToGEntity]:
        """Get full entity object by name from graph."""
        query = """
        MATCH (e:Entity {name: $name})
        """

        if document_ids:
            query += """
            WHERE e.document_id IN $document_ids
            """

        query += """
        RETURN e.id as id, e.name as name, e.type as type,
               e.description as description, e.confidence as confidence,
               e.document_id as document_id
        LIMIT 1
        """

        with self.graph_service.get_session() as session:
            result = session.run(query, {"name": entity_name, "document_ids": document_ids})
            record = result.single()

            if record:
                entity = ToGEntity(
                    id=record["id"],
                    name=record["name"],
                    type=record["type"],
                    description=record.get("description"),
                    confidence=record.get("confidence", 1.0),
                    document_id=record.get("document_id"),
                )
                return entity

            return None

    async def _explore_relations(
        self, question: str, entities: List[ToGEntity], config: ToGConfig
    ) -> List[ToGRelation]:
        """
        Find and score relations connected to current entities.

        Returns:
            List of scored relations to explore
        """
        logger.info(f"Exploring relations for {len(entities)} entities")

        # Step 1: Get relations from graph (use optimized version)
        available_relations = self._get_entity_relations_optimized(entities, config.document_ids)

        if not available_relations:
            logger.warning(f"No relations found for entities: {[e.name for e in entities]}")
            return []

        # Step 2: Filter out already explored relations (avoid cycles)
        new_relations = [
            r for r in available_relations if r["relation_type"] not in self.explored_relations
        ]

        if not new_relations:
            logger.warning("All relations already explored")
            return []

        logger.debug(f"Found {len(new_relations)} new relations to score")

        # Step 3: Use pruning method to score relations
        relation_names = [r["relation_type"] for r in new_relations if r.get("relation_type")]

        if not relation_names:
            logger.warning("No valid relation names found after filtering")
            return []

        scored_relations = await self.pruning_method.score_relations(
            question=question,
            relations=relation_names,
            context={
                "entities": ", ".join([e.name for e in entities if e.name]),
                "previous_relations": (
                    ", ".join([r for r in self.explored_relations if r]) if self.explored_relations else "None"
                ),
            },
        )

        # Step 4: Sort by score and select top relations
        scored_relations.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_relations = scored_relations[: config.search_width]

        # Step 5: Convert to ToGRelation objects and mark as explored
        result_relations = []
        for rel_data in top_relations:
            relation_type = rel_data.get("relation_type", "")
            if relation_type:
                # Find the source entity (first entity in the list for simplicity)
                # In practice, this should be more sophisticated
                source_entity = entities[0] if entities else None

                if source_entity:
                    # Create a placeholder target entity - will be resolved during expansion
                    target_entity = ToGEntity(
                        id=f"temp_{relation_type}",
                        name=f"Target of {relation_type}",
                        type="UNKNOWN",
                    )

                    relation = ToGRelation(
                        type=relation_type,
                        source_entity=source_entity,
                        target_entity=target_entity,
                        description=rel_data.get("reasoning", ""),
                        score=rel_data.get("score", 0.0),
                    )
                    result_relations.append(relation)

                    # Mark as explored
                    self.explored_relations.add(relation_type)

        logger.info(
            f"Selected {len(result_relations)} relations: {[r.type for r in result_relations]}"
        )

        return result_relations

    def _get_entity_relations(
        self, entities: List[ToGEntity], document_ids: Optional[List[int]]
    ) -> List[Dict]:
        """Get unique relation types connected to given entities."""
        entity_names = [e.name for e in entities]

        query = """
        MATCH (e:Entity)-[r:RELATED_TO]->(other:Entity)
        WHERE e.name IN $entity_names
        """

        if document_ids:
            query += """
            AND e.document_id IN $document_ids
            AND other.document_id IN $document_ids
            """

        query += """
        RETURN DISTINCT r.type as relation_type,
                        count(*) as frequency,
                        avg(r.confidence) as avg_confidence
        ORDER BY frequency DESC
        LIMIT 50
        """

        with self.graph_service.get_session() as session:
            result = session.run(
                query, {"entity_names": entity_names, "document_ids": document_ids}
            )

            relations = []
            for record in result:
                relation_type = record.get("relation_type")
                if relation_type:  # Skip None/null relation types
                    relations.append(
                        {
                            "relation_type": relation_type,
                            "frequency": record.get("frequency", 0),
                            "avg_confidence": record.get("avg_confidence", 0.0),
                        }
                    )
                else:
                    logger.warning(f"Skipping relation with null type for entities: {entity_names[:3]}")

            logger.debug(f"Found {len(relations)} valid relations for {len(entity_names)} entities")
            return relations

    def _get_entity_relations_optimized(
        self, entities: List[ToGEntity], document_ids: Optional[List[int]]
    ) -> List[Dict]:
        """Optimized version of _get_entity_relations with better query planning."""
        entity_names = [e.name for e in entities]

        # Use UNION ALL for better performance with filtered queries
        if document_ids:
            query = """
            MATCH (e:Entity)-[r:RELATED_TO]->(other:Entity)
            WHERE e.name IN $entity_names
            AND e.document_id IN $document_ids
            AND other.document_id IN $document_ids
            AND r.confidence > 0.3
            WITH COALESCE(r.type, r.description, type(r)) as relation_type, count(*) as frequency, avg(r.confidence) as avg_confidence
            WHERE relation_type IS NOT NULL
            RETURN relation_type, frequency, avg_confidence
            ORDER BY frequency DESC
            LIMIT 50
            """
        else:
            query = """
            MATCH (e:Entity)-[r:RELATED_TO]->(other:Entity)
            WHERE e.name IN $entity_names
            WITH COALESCE(r.type, r.description, type(r)) as relation_type, count(*) as frequency, avg(r.confidence) as avg_confidence
            WHERE relation_type IS NOT NULL
            RETURN relation_type, frequency, avg_confidence
            ORDER BY frequency DESC
            LIMIT 50
            """

        with self.graph_service.get_session() as session:
            result = session.run(
                query, {"entity_names": entity_names, "document_ids": document_ids}
            )

            relations = []
            for record in result:
                relation_type = record.get("relation_type")
                if relation_type:  # Skip None/null relation types
                    relations.append(
                        {
                            "relation_type": relation_type,
                            "frequency": record.get("frequency", 0),
                            "avg_confidence": record.get("avg_confidence", 0.0),
                        }
                    )
                else:
                    logger.warning(f"Skipping relation with null type for entities: {entity_names[:3]}")

            logger.debug(f"Found {len(relations)} valid relations for {len(entity_names)} entities")
            return relations

    async def _expand_entity_from_relation(
        self, relation: ToGRelation, document_ids: Optional[List[int]]
    ) -> Optional[ToGEntity]:
        """
        Expand to find target entities for a given relation.

        Uses LLM to score candidate entities and selects the best ones.
        """
        logger.debug(f"Expanding entities for relation: {relation.type}")

        # Get candidate entities connected via this relation type
        candidate_entities = self._get_related_entities(
            relation.source_entity.name, relation.type, document_ids
        )

        if not candidate_entities:
            logger.debug(f"No entities found for relation {relation.type}")
            return None

        # If only one candidate, return it directly
        if len(candidate_entities) == 1:
            return candidate_entities[0]

        # Use LLM to score and select the best entity
        scored_entities = await self._score_entities_for_relation(
            question, relation, candidate_entities
        )

        # Return the highest scored entity
        if scored_entities:
            best_entity = max(scored_entities, key=lambda x: x.get("score", 0))
            entity_name = best_entity.get("entity_name", "")

            # Find the actual entity object
            for entity in candidate_entities:
                if entity.name == entity_name:
                    return entity

        # Fallback: return first candidate
        return candidate_entities[0] if candidate_entities else None

    def _add_triplet(
        self,
        subject: str,
        relation: str,
        object: str,
        confidence: float = 1.0,
        source: Optional[str] = None,
    ):
        """Add a triplet to the collected triplets set."""
        triplet = ToGTriplet(
            subject=subject, relation=relation, object=object, confidence=confidence, source=source
        )
        self.retrieved_triplets.add(triplet)

    def _get_related_entities(
        self, source_entity_name: str, relation_type: str, document_ids: Optional[List[int]]
    ) -> List[ToGEntity]:
        """Get entities related to source entity via specific relation type."""
        query = """
        MATCH (source:Entity)-[r:RELATED_TO]->(target:Entity)
        WHERE source.name = $source_name
        """

        if relation_type and relation_type != "RELATES_TO":
            query += " AND r.type = $relation_type"

        if document_ids:
            query += (
                " AND source.document_id IN $document_ids AND target.document_id IN $document_ids"
            )

        query += """
        RETURN target.id as id, target.name as name, target.type as type,
           target.description as description, target.confidence as confidence,
               target.document_id as document_id, r.confidence as relation_confidence
        ORDER BY r.confidence DESC, target.mention_count DESC
        LIMIT 20
        """

        with self.graph_service.get_session() as session:
            result = session.run(
                query,
                {
                    "source_name": source_entity_name,
                    "relation_type": relation_type,
                    "document_ids": document_ids,
                },
            )

            entities = []
            for record in result:
                entities.append(
                    ToGEntity(
                        id=record["id"],
                        name=record["name"],
                        type=record["type"],
                        description=record.get("description"),
                        confidence=record.get("confidence", 1.0),
                        document_id=record.get("document_id"),
                    )
                )

            return entities

    async def _score_entities_for_relation(
        self, question: str, relation: ToGRelation, candidate_entities: List[ToGEntity]
    ) -> List[Dict]:
        """
        Use pruning method to score candidate entities for a given relation and question context.
        """
        # Convert ToGEntity objects to dict format expected by pruning methods
        entity_dicts = [
            {
                "entity_name": e.name,
                "description": e.description or "",
                "entity_type": e.type,
                "confidence": e.confidence,
            }
            for e in candidate_entities
        ]

        scored_entities = await self.pruning_method.score_entities(
            question=question,
            entities=entity_dicts,
            context={"relation": relation.type, "source_entity": relation.source_entity.name},
        )

        return scored_entities

    async def _check_sufficiency(
        self, question: str, relations: List[ToGRelation], config: ToGConfig
    ) -> Dict[str, Any]:
        """
        Check if current relations provide sufficient information to answer the question.

        Returns:
            Dict with sufficiency assessment
        """
        logger.debug("Checking sufficiency of current relations")

        if not relations:
            return {"sufficient": False, "score": 0.0, "reasoning": "No relations to evaluate"}

        # Format relations for prompt
        relation_summary = []
        for rel in relations:
            relation_summary.append(
                f"{rel.source_entity.name} --[{rel.type}]--> {rel.target_entity.name}"
            )
        relation_text = "; ".join(relation_summary)

        prompt = TOG_SUFFICIENCY_CHECK_PROMPT.format(question=question, relations=relation_text)

        response = await self.llm_service.generate_text(
            prompt=prompt, temperature=config.reasoning_temp
        )

        result = self.llm_service._parse_json_response(response)

        sufficiency = {
            "sufficient": result.get("sufficient", False),
            "score": result.get("confidence_score", 0.0),
            "reasoning": result.get("reasoning", ""),
        }

        logger.debug(f"Sufficiency check result: {sufficiency}")
        return sufficiency

    async def _generate_final_answer(self, question: str, config: ToGConfig) -> str:
        """
        Generate final answer based on explored reasoning path.
        """
        logger.info("Generating final answer from reasoning path")

        if not self.reasoning_path.steps:
            return "No reasoning path available to generate an answer."

        # Format the reasoning path for the LLM
        path_summary = []
        for step in self.reasoning_path.steps:
            entities = [e.name for e in step.entities_explored]
            relations = [
                f"{r.source_entity.name}--[{r.type}]-->{r.target_entity.name}"
                for r in step.relations_selected
            ]
            path_summary.append(f"Step {step.depth}: Entities {entities}, Relations {relations}")

        reasoning_text = "; ".join(path_summary)

        prompt = TOG_FINAL_ANSWER_PROMPT.format(question=question, reasoning_path=reasoning_text)

        response = await self.llm_service.generate_text(
            prompt=prompt, temperature=config.reasoning_temp
        )

        # Extract answer from response
        result = self.llm_service._parse_json_response(response)
        answer = result.get("answer", response)

        # Update confidence if available
        if "confidence" in result:
            self.reasoning_path.confidence_score = result["confidence"]

        return answer

    # Error Handling and Edge Cases

    async def process_query_safe(self, question: str, config: ToGConfig) -> ToGReasoningPath:
        """
        Safe wrapper for process_query with comprehensive error handling and fallbacks.
        """
        import time

        start_time = time.time()

        try:
            return await self._process_query_impl(question, config)
        except Exception as e:
            logger.error(f"ToG reasoning failed: {str(e)}", exc_info=True)

            # Fallback to basic graph search
            return await self._fallback_reasoning(question, config, start_time)

    async def _process_query_impl(self, question: str, config: ToGConfig) -> ToGReasoningPath:
        """
        Internal implementation with safeguards.
        """
        # Reset state
        self.explored_entities.clear()
        self.explored_relations.clear()
        self.reasoning_path = ToGReasoningPath()
        self.retrieved_triplets.clear()

        # Initialize pruning method
        from app.services.pruning_methods import create_pruning_method

        self.pruning_method = create_pruning_method(
            config.pruning_method, llm_service=self.llm_service
        )

        # Phase 1: Extract topic entities with error handling
        topic_entities = await self._extract_topic_entities_safe(question, config.document_ids)
        if not topic_entities:
            raise ValueError("No topic entities found in knowledge graph")

        # Initialize with topic entities
        current_entities = []
        for entity_name in topic_entities:
            entity = self._get_entity_by_name(entity_name, config.document_ids)
            if entity:
                current_entities.append(entity)
                self.explored_entities.add(entity)

        if not current_entities:
            raise ValueError("No entities found in graph matching topic entities")

        # Phase 2: Iterative exploration with safeguards
        max_iterations = 10
        iteration_count = 0

        for depth in range(config.search_depth):
            iteration_count += 1
            if iteration_count > max_iterations:
                logger.warning(f"Max iterations ({max_iterations}) reached")
                break

            logger.info(f"Exploring depth {depth + 1}/{config.search_depth}")

            # Explore relations for current entities
            relations = await self._explore_relations_safe(question, current_entities, config)

            # Create reasoning step
            step = ToGReasoningStep(
                depth=depth + 1,
                entities_explored=current_entities,
                relations_selected=relations
            )

            if not relations:
                logger.info(f"No new relations found at depth {depth + 1}")
                break

            # Get target entities from relations
            next_entities = []
            for relation in relations:
                target_entity = await self._expand_entity_from_relation_safe(
                    relation, config.document_ids
                )
                if target_entity and target_entity not in self.explored_entities:
                    next_entities.append(target_entity)
                    self.explored_entities.add(target_entity)

                    # Track triplet
                    self._add_triplet(
                        subject=relation.source_entity.name,
                        relation=relation.type,
                        object=target_entity.name,
                        confidence=relation.confidence,
                        source=f"depth_{depth + 1}",
                    )

            # Limit entities per depth
            next_entities = next_entities[: config.num_retain_entity]

            # Check sufficiency if enabled
            if config.enable_sufficiency_check:
                sufficiency = await self._check_sufficiency_safe(question, relations, config)
                step.sufficiency_score = sufficiency.get("score", 0.0)
                step.reasoning_notes = sufficiency.get("reasoning", "")

                if sufficiency.get("sufficient", False):
                    logger.info(f"Sufficiency reached at depth {depth + 1}")
                    self.reasoning_path.sufficiency_status = "sufficient"
                    self.reasoning_path.steps.append(step)
                    break
            else:
                self.reasoning_path.sufficiency_status = "unknown"

            # Add step to reasoning path
            self.reasoning_path.steps.append(step)

            if not next_entities:
                logger.info(f"No new entities to explore at depth {depth + 1}")
                break

            # Cycle detection
            if self._detect_cycle(current_entities, next_entities):
                logger.warning("Cycle detected, stopping exploration")
                break

            # Prepare for next depth
            current_entities = next_entities

        # Phase 3: Generate final answer
        final_answer = await self._generate_final_answer_safe(question, config)
        self.reasoning_path.final_answer = final_answer

        # Add collected triplets to reasoning path
        self.reasoning_path.retrieved_triplets = list(self.retrieved_triplets)

        logger.info(f"ToG reasoning completed with {len(self.retrieved_triplets)} triplets")
        return self.reasoning_path

    async def _extract_topic_entities_safe(
        self, question: str, document_ids: Optional[List[int]]
    ) -> List[str]:
        """Extract topic entities with fallback strategies."""
        try:
            entities = await self._extract_topic_entities(question, document_ids)
            if entities:
                return entities
        except Exception as e:
            logger.warning(f"Primary entity extraction failed: {e}")

        # Fallback: Try without document filter
        if document_ids:
            try:
                logger.info("Retrying entity extraction without document filter")
                entities = await self._extract_topic_entities(question, None)
                if entities:
                    return entities
            except Exception as e:
                logger.warning(f"Fallback entity extraction failed: {e}")

        # Final fallback: Fuzzy matching on question
        return self._fuzzy_match_entities_from_question(
            question, self._get_available_entities(document_ids), 3
        )

    async def _explore_relations_safe(
        self, question: str, entities: List[ToGEntity], config: ToGConfig
    ) -> List[ToGRelation]:
        """Explore relations with error handling."""
        try:
            return await self._explore_relations(question, entities, config)
        except Exception as e:
            logger.error(f"Relation exploration failed: {e}")
            return []

    async def _expand_entity_from_relation_safe(
        self, relation: ToGRelation, document_ids: Optional[List[int]]
    ) -> Optional[ToGEntity]:
        """Expand entity from relation with error handling."""
        try:
            return await self._expand_entity_from_relation(relation, document_ids)
        except Exception as e:
            logger.error(f"Entity expansion failed for relation {relation.type}: {e}")
            return None

    async def _check_sufficiency_safe(
        self, question: str, relations: List[ToGRelation], config: ToGConfig
    ) -> Dict[str, Any]:
        """Check sufficiency with error handling."""
        try:
            return await self._check_sufficiency(question, relations, config)
        except Exception as e:
            logger.error(f"Sufficiency check failed: {e}")
            return {
                "sufficient": False,
                "score": 0.0,
                "reasoning": f"Error during sufficiency evaluation: {str(e)}",
            }

    async def _generate_final_answer_safe(self, question: str, config: ToGConfig) -> str:
        """Generate final answer with error handling."""
        try:
            return await self._generate_final_answer(question, config)
        except Exception as e:
            logger.error(f"Final answer generation failed: {e}")
            return f"Unable to generate comprehensive answer due to processing error: {str(e)}. Basic analysis suggests the question requires multi-hop reasoning through the knowledge graph."

    def _detect_cycle(
        self, current_entities: List[ToGEntity], next_entities: List[ToGEntity]
    ) -> bool:
        """Detect if we're revisiting the same entities (cycle)."""
        if len(self.reasoning_path.steps) < 2:
            return False

        # Check if current entities overlap significantly with previous steps
        current_names = set(e.name for e in current_entities)
        next_names = set(e.name for e in next_entities)

        # Check overlap with last step
        if len(self.reasoning_path.steps) >= 1:
            prev_names = set(e.name for e in self.reasoning_path.steps[-1].entities_explored)
            overlap = len(current_names & prev_names)
            if overlap / max(len(current_names), 1) > 0.8:
                return True

        return False

    async def _fallback_reasoning(
        self, question: str, config: ToGConfig, start_time: float
    ) -> ToGReasoningPath:
        """Fallback reasoning when main process fails."""
        import time

        logger.info("Using fallback reasoning strategy")

        # Create a basic reasoning path
        reasoning_path = ToGReasoningPath()
        reasoning_path.sufficiency_status = "unknown"

        # Try to extract some basic entities
        try:
            available_entities = self._get_available_entities(config.document_ids)
            topic_entities = self._fuzzy_match_entities_from_question(
                question, available_entities, 2
            )

            if topic_entities:
                # Create a simple reasoning step
                entities = []
                for entity_name in topic_entities[:2]:  # Limit to 2
                    entity = self._get_entity_by_name(entity_name, config.document_ids)
                    if entity:
                        entities.append(entity)

                if entities:
                    step = ToGReasoningStep(
                        depth=1,
                        entities_explored=entities,
                        relations_selected=[],
                        sufficiency_score=0.0,
                        reasoning_notes="Fallback analysis due to processing error",
                    )
                    reasoning_path.steps.append(step)

        except Exception as e:
            logger.error(f"Fallback entity extraction failed: {e}")

        # Generate fallback answer
        reasoning_path.final_answer = (
            "I'm unable to perform full multi-hop reasoning due to a processing error. "
            "However, I can provide some basic analysis of your question. "
            f"The question appears to be: '{question}'. "
            "For more comprehensive answers involving complex relationships, "
            "please try rephrasing your question or contact support if the issue persists."
        )

        reasoning_path.confidence_score = 0.1

        processing_time = int((time.time() - start_time) * 1000)
        logger.warning(f"Fallback reasoning completed in {processing_time}ms")

        return reasoning_path
