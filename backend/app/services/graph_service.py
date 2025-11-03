"""
Neo4j graph database service for knowledge graph management
Handles entity creation, relationship management, and graph queries
"""

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

from neo4j import Session

from app.db.neo4j import get_neo4j_session

logger = logging.getLogger(__name__)


class GraphService:
    """Service for Neo4j graph operations and knowledge graph management"""

    def __init__(self):
        """Initialize graph service"""
        self.session = None

    def get_session(self) -> Session:
        """Get or create Neo4j session"""
        if not self.session:
            self.session = get_neo4j_session()
        return self.session

    def init_schema(self) -> bool:
        """
        Initialize Neo4j schema with constraints and indexes

        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.get_session()

            # Create constraints for uniqueness
            constraints = [
                "CREATE CONSTRAINT entity_name_type IF NOT EXISTS FOR (e:Entity) REQUIRE (e.name, e.type) IS UNIQUE",
                "CREATE CONSTRAINT document_name IF NOT EXISTS FOR (d:Document) REQUIRE d.name IS UNIQUE",
                "CREATE CONSTRAINT textunit_id IF NOT EXISTS FOR (t:TextUnit) REQUIRE t.id IS UNIQUE",
                "CREATE CONSTRAINT community_id IF NOT EXISTS FOR (c:Community) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.id IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"Created constraint: {constraint[:50]}...")
                except Exception as e:
                    if "already exists" not in str(e):
                        logger.warning(f"Constraint creation warning: {e}")

            # Create indexes for performance
            indexes = [
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
            "CREATE INDEX textunit_doc_id IF NOT EXISTS FOR (t:TextUnit) ON (t.document_id)",
            "CREATE INDEX entity_confidence IF NOT EXISTS FOR (e:Entity) ON (e.confidence)",
            "CREATE INDEX relationship_type IF NOT EXISTS FOR (r:MENTIONED_IN) ON (r.type)",
            "CREATE INDEX claim_type IF NOT EXISTS FOR (c:Claim) ON (c.claim_type)",
            "CREATE INDEX claim_status IF NOT EXISTS FOR (c:Claim) ON (c.status)",
                # ToG-specific indexes for optimized traversal
                "CREATE INDEX entity_name_lookup IF NOT EXISTS FOR (e:Entity) ON (e.name)",
                "CREATE INDEX entity_document IF NOT EXISTS FOR (e:Entity) ON (e.document_id)",
                "CREATE INDEX entity_mention_count IF NOT EXISTS FOR (e:Entity) ON (e.mention_count)",
                "CREATE INDEX relation_type IF NOT EXISTS FOR ()-[r:RELATES_TO]-() ON (r.type)",
                "CREATE INDEX relation_confidence IF NOT EXISTS FOR ()-[r:RELATES_TO]-() ON (r.confidence)",
                "CREATE INDEX entity_name_doc_composite IF NOT EXISTS FOR (e:Entity) ON (e.name, e.document_id)",
            ]

            for index in indexes:
                try:
                    session.run(index)
                    logger.info(f"Created index: {index[:50]}...")
                except Exception as e:
                    if "already exists" not in str(e):
                        logger.warning(f"Index creation warning: {e}")

            logger.info("✅ Graph schema initialized")
            return True

        except Exception as e:
            logger.error(f"❌ Schema initialization error: {e}")
            return False

    def create_document_node(
        self,
        document_id: str,
        document_name: str,
        file_path: str,
    ) -> bool:
        """
        Create a Document node in the graph

        Args:
            document_id: Unique document identifier
            document_name: Human-readable document name
            file_path: Path to the document file

        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.get_session()

            query = """
            MERGE (d:Document {
                id: $document_id,
                name: $document_name,
                file_path: $file_path,
                created_at: datetime(),
                status: 'pending'
            })
            RETURN d
            """

            result = session.run(
                query,
                document_id=str(document_id),  # Convert UUID to string for Neo4j
                document_name=document_name,
                file_path=file_path,
            )

            if result.single():
                logger.info(f"Created document node: {document_name}")
                return True
            return False

        except Exception as e:
            logger.error(f"Document creation error: {e}")
            return False

    def create_textunit_node(
        self,
        textunit_id: str,
        document_id: str,
        text: str,
        start_char: int,
        end_char: int,
    ) -> bool:
        """
        Create a TextUnit (chunk) node and link to document

        Args:
            textunit_id: Unique text unit identifier
            document_id: Parent document ID
            text: The text content
            start_char: Starting character position
            end_char: Ending character position

        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.get_session()

            query = """
            MERGE (d:Document {id: $document_id})
            CREATE (t:TextUnit {
                id: $textunit_id,
                document_id: $document_id,
                text: $text,
                start_char: $start_char,
                end_char: $end_char,
                created_at: datetime()
            })
            CREATE (t)-[:PART_OF]->(d)
            RETURN t
            """

            result = session.run(
                query,
                textunit_id=textunit_id,
                document_id=str(document_id),  # Convert UUID to string for Neo4j
                text=text,
                start_char=start_char,
                end_char=end_char,
            )

            if result.single():
                return True
            return False

        except Exception as e:
            logger.error(f"TextUnit creation error: {e}")
            return False

    def create_or_merge_entity(
        self,
        name: str,
        entity_type: str,
        description: str,
        confidence: float = 0.8,
    ) -> Optional[str]:
        """
        Create or merge an entity node with deduplication

        Args:
            name: Entity name
            entity_type: Type of entity (PERSON, ORGANIZATION, etc.)
            description: Entity description
            confidence: Confidence score 0.0-1.0

        Returns:
            Entity ID if successful, None otherwise
        """
        try:
            session = self.get_session()

            # Generate entity ID using name and type
            entity_key = f"{name.lower().strip()}:{entity_type.lower()}"
            entity_id = hashlib.md5(entity_key.encode()).hexdigest()[:16]

            query = """
            MERGE (e:Entity {
                name: $name,
                type: $entity_type
            })
            ON CREATE SET
                e.id = $entity_id,
                e.description = $description,
                e.confidence = $confidence,
                e.created_at = datetime(),
                e.mention_count = 1
            ON MATCH SET
                e.mention_count = e.mention_count + 1,
                e.updated_at = datetime(),
                e.confidence = CASE WHEN $confidence > e.confidence THEN $confidence ELSE e.confidence END
            RETURN e.id as id
            """

            result = session.run(
                query,
                name=name,
                entity_type=entity_type,
                entity_id=entity_id,
                description=description,
                confidence=confidence,
            )

            record = result.single()
            if record:
                return record["id"]
            return None

        except Exception as e:
            logger.error(f"Entity creation error: {e}")
            return None

    def create_mention_relationship(
        self,
        entity_id: str,
        textunit_id: str,
    ) -> bool:
        """
        Create a MENTIONED_IN relationship between entity and text unit

        Args:
            entity_id: Entity ID
            textunit_id: TextUnit ID

        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.get_session()

            query = """
            MATCH (e:Entity {id: $entity_id})
            MATCH (t:TextUnit {id: $textunit_id})
            MERGE (e)-[r:MENTIONED_IN]->(t)
            ON CREATE SET r.created_at = datetime()
            RETURN r
            """

            result = session.run(
                query,
                entity_id=entity_id,
                textunit_id=textunit_id,
            )

            return result.single() is not None

        except Exception as e:
            logger.error(f"Mention relationship creation error: {e}")
            return False

    def create_relationship(
        self,
        source_entity_id: str,
        target_entity_id: str,
        relationship_type: str,
        description: str,
        confidence: float = 0.8,
    ) -> bool:
        """
        Create a relationship between two entities

        Args:
            source_entity_id: Source entity ID
            target_entity_id: Target entity ID
            relationship_type: Type of relationship
            description: Relationship description
            confidence: Confidence score

        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.get_session()

            # Use relationship type as the Neo4j relationship label
            query = f"""
            MATCH (source:Entity {{id: $source_id}})
            MATCH (target:Entity {{id: $target_id}})
            MERGE (source)-[r:{relationship_type}]->(target)
            ON CREATE SET
                r.description = $description,
                r.confidence = $confidence,
                r.created_at = datetime()
            ON MATCH SET
                r.confidence = CASE WHEN $confidence > r.confidence THEN $confidence ELSE r.confidence END,
                r.updated_at = datetime()
            RETURN r
            """

            result = session.run(
                query,
                source_id=source_entity_id,
                target_id=target_entity_id,
                description=description,
                confidence=confidence,
            )

            return result.single() is not None

        except Exception as e:
            logger.error(f"Relationship creation error: {e}")
            return False

    def find_entity_by_name(
        self, name: str, entity_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find an entity by name and optionally type

        Args:
            name: Entity name to search for
            entity_type: Optional entity type filter

        Returns:
            Entity data if found, None otherwise
        """
        try:
            session = self.get_session()

            if entity_type:
                query = """
                MATCH (e:Entity {name: $name, type: $type})
                RETURN e.id as id, e.name as name, e.type as type, e.description as description, e.confidence as confidence
                LIMIT 1
                """
                result = session.run(query, name=name, type=entity_type)
            else:
                query = """
                MATCH (e:Entity {name: $name})
                RETURN e.id as id, e.name as name, e.type as type, e.description as description, e.confidence as confidence
                LIMIT 1
                """
                result = session.run(query, name=name)

            record = result.single()
            if record:
                return dict(record)
            return None

        except Exception as e:
            logger.error(f"Entity lookup error: {e}")
            return None

    def get_top_entities(
        self, limit: int = 10, document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get top entities from the graph, ordered by mention count and confidence

        Args:
            limit: Maximum number of entities to return
            document_id: Optional document ID to filter entities

        Returns:
            List of entity data dictionaries
        """
        try:
            session = self.get_session()

            if document_id:
                query = """
                MATCH (d:Document {id: $document_id})<-[:PART_OF]-(t:TextUnit)<-[:MENTIONED_IN]-(e:Entity)
                RETURN DISTINCT e.id as id, e.name as name, e.type as type, 
                       e.description as description, e.confidence as confidence,
                       e.mention_count as mention_count
                ORDER BY e.mention_count DESC, e.confidence DESC
                LIMIT $limit
                """
                result = session.run(query, document_id=document_id, limit=limit)
            else:
                query = """
                MATCH (e:Entity)
                RETURN e.id as id, e.name as name, e.type as type, 
                       e.description as description, e.confidence as confidence,
                       COALESCE(e.mention_count, 1) as mention_count
                ORDER BY mention_count DESC, e.confidence DESC
                LIMIT $limit
                """
                result = session.run(query, limit=limit)

            entities = []
            for record in result:
                entities.append(dict(record))

            return entities

        except Exception as e:
            logger.error(f"Top entities retrieval error: {e}")
            return []

    def get_entity_context(
        self,
        entity_id: str,
        hop_limit: int = 2,
        include_text: bool = True,
    ) -> Dict[str, Any]:
        """
        Get context around an entity (related entities, relationships, and text units)
        Following Microsoft GraphRAG methodology

        Args:
            entity_id: Entity to get context for
            hop_limit: How many hops to traverse for entity relationships
            include_text: Whether to include text units (default True per GraphRAG)

        Returns:
            Dict with entities, relationships, and text_units
        """
        try:
            session = self.get_session()

            # PART 1: Get related entities via semantic relationships (NOT IN_COMMUNITY)
            # This follows Microsoft GraphRAG's local search pattern
            # Note: GraphRAG uses generic RELATED_TO relationships with descriptions, not typed relationships
            entity_query = """
            MATCH (e:Entity {id: $entity_id})

            // Get directly related entities via RELATED_TO relationships
            OPTIONAL MATCH (e)-[r1:RELATED_TO]-(related1:Entity)

            // Get 2-hop related entities if hop_limit >= 2
            OPTIONAL MATCH (e)-[r1:RELATED_TO]-
                          (intermediate:Entity)-[r2:RELATED_TO]-(related2:Entity)
            WHERE $hop_limit >= 2
            
            WITH e, 
                 COLLECT(DISTINCT {
                     entity: related1, 
                     relationship: r1,
                     distance: 1
                 }) + COLLECT(DISTINCT {
                     entity: related2,
                     relationship: r2, 
                     distance: 2
                 }) AS all_related
            
            // Filter out nulls and duplicates
            UNWIND all_related AS rel_item
            WITH e, rel_item
            WHERE rel_item.entity IS NOT NULL
            
            WITH e,
                 COLLECT(DISTINCT {
                     id: rel_item.entity.id,
                     name: rel_item.entity.name,
                     type: rel_item.entity.type,
                     description: rel_item.entity.description,
                     distance: rel_item.distance,
                     relationship_type: type(rel_item.relationship)
                 }) AS related_entities
            
            RETURN
                e.id AS central_entity_id,
                e.name AS central_entity_name,
                e.type AS central_entity_type,
                e.description AS central_entity_description,
                related_entities
            LIMIT 1
            """

            result = session.run(entity_query, entity_id=entity_id, hop_limit=hop_limit)
            record = result.single()

            if not record:
                logger.debug(f"Entity {entity_id} not found in graph")
                return {}

            data = record.data()
            context = {
                "central_entity_id": data.get("central_entity_id"),
                "central_entity_name": data.get("central_entity_name"),
                "central_entity_type": data.get("central_entity_type"),
                "central_entity_description": data.get("central_entity_description"),
                "related_entities": data.get("related_entities") or [],
            }

            # PART 2: Get text units containing this entity (Microsoft GraphRAG requirement)
            # This provides actual document text for LLM context
            if include_text:
                text_query = """
                MATCH (e:Entity {id: $entity_id})-[:MENTIONED_IN]->(t:TextUnit)
                RETURN 
                    t.id AS text_unit_id,
                    t.text AS text,
                    t.document_id AS document_id,
                    t.start_char AS start_char,
                    t.end_char AS end_char
                ORDER BY t.start_char
                LIMIT 10
                """

                text_results = session.run(text_query, entity_id=entity_id)
                text_units = []

                for text_record in text_results:
                    text_data = text_record.data()
                    text_units.append(
                        {
                            "text_unit_id": text_data.get("text_unit_id"),
                            "text": text_data.get("text"),
                            "document_id": text_data.get("document_id"),
                            "start_char": text_data.get("start_char"),
                            "end_char": text_data.get("end_char"),
                        }
                    )

                context["text_units"] = text_units
                logger.debug(f"Retrieved {len(text_units)} text units for entity {entity_id}")

            return context

        except Exception as e:
            logger.warning(f"Context retrieval error for entity {entity_id}: {e}")
            return {}

    def get_document_statistics(self, document_id: str) -> Dict[str, Any]:
        """
        Get statistics for a document in the graph

        Args:
            document_id: Document to get stats for

        Returns:
            Statistics dictionary
        """
        try:
            session = self.get_session()

            query = """
            MATCH (d:Document {id: $doc_id})
            RETURN {
                document_name: d.name,
                textunits: size((d)<-[:PART_OF]-()),
                entities: size((d)<-[:MENTIONED_IN]-()-[:MENTIONED_IN]->()),
                created_at: d.created_at,
                status: d.status
            } as stats
            """

            result = session.run(query, doc_id=document_id)
            record = result.single()

            if record:
                return dict(record["stats"])
            return {}

        except Exception as e:
            logger.error(f"Statistics retrieval error: {e}")
            return {}

    def get_graph_statistics(self) -> Dict[str, Any]:
        """
        Get overall graph statistics

        Returns:
            Statistics dictionary
        """
        try:
            session = self.get_session()

            queries = {
                "documents": "MATCH (d:Document) RETURN count(d) as count",
                "textunits": "MATCH (t:TextUnit) RETURN count(t) as count",
                "entities": "MATCH (e:Entity) RETURN count(e) as count",
                "relationships": "MATCH ()-[r]->() WHERE r:RELATED_TO OR r:MENTIONS OR r:CAUSES OR r:SUPPORTS OR r:OPPOSES RETURN count(r) as count",
            }

            stats = {}
            for key, query in queries.items():
                result = session.run(query)
                record = result.single()
                stats[key] = record["count"] if record else 0

            return stats

        except Exception as e:
            logger.error(f"Graph statistics error: {e}")
            return {}

    def create_claim_node(
        self,
        subject_entity_name: str,
        object_entity_name: str,
        claim_type: str,
        status: str,
        description: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        source_text: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a Claim node in the graph

        Args:
            subject_entity_name: Subject entity (who makes/commits the claim)
            object_entity_name: Object entity (who is affected/reports)
            claim_type: Type/category of claim
            status: TRUE, FALSE, or SUSPECTED
            description: Detailed claim description
            start_date: Claim start date (ISO-8601 format)
            end_date: Claim end date (ISO-8601 format)
            source_text: Source text supporting the claim

        Returns:
            Claim ID if successful, None otherwise
        """
        try:
            session = self.get_session()

            # Generate claim ID using subject, object, type, description, and source_text
            # Include source_text to ensure uniqueness when same claim appears in different contexts
            claim_key = f"{subject_entity_name}:{object_entity_name}:{claim_type}:{description}:{source_text or ''}"
            claim_id = hashlib.md5(claim_key.encode()).hexdigest()[:16]

            # Use MERGE instead of CREATE to handle duplicates gracefully
            # This follows Microsoft GraphRAG's approach of deduplicating claims
            query = """
            MERGE (c:Claim {id: $claim_id})
            ON CREATE SET
                c.subject = $subject,
                c.object = $object,
                c.claim_type = $claim_type,
                c.status = $status,
                c.description = $description,
                c.start_date = $start_date,
                c.end_date = $end_date,
                c.source_text = $source_text,
                c.created_at = datetime(),
                c.occurrence_count = 1
            ON MATCH SET
                c.occurrence_count = c.occurrence_count + 1,
                c.updated_at = datetime()
            RETURN c.id as id
            """

            result = session.run(
                query,
                claim_id=claim_id,
                subject=subject_entity_name,
                object=object_entity_name,
                claim_type=claim_type,
                status=status,
                description=description,
                start_date=start_date,
                end_date=end_date,
                source_text=source_text,
            )

            # Get first record - use data() to avoid single() warning if multiple records
            records = list(result)
            if records:
                record = records[0]  # Get first record
                if len(records) > 1:
                    logger.debug(f"Query returned {len(records)} records for claim, using first one")
                logger.info(f"Created/updated claim: {subject_entity_name} -> {claim_type}")
                return record["id"]
            else:
                logger.warning(f"No record returned for claim: {subject_entity_name} -> {claim_type}")
                return None

        except Exception as e:
            # Don't log constraint violations as errors since we handle them with MERGE
            if "ConstraintValidationFailed" in str(e) or "already exists" in str(e):
                logger.debug(f"Claim already exists (expected with MERGE): {subject_entity_name} -> {claim_type}")
                return claim_id  # Return the claim_id even if it already exists
            else:
                logger.error(f"Claim creation error: {e}")
                return None

    def link_claim_to_entities(
        self,
        claim_id: str,
        subject_entity_name: str,
        object_entity_name: Optional[str] = None,
    ) -> bool:
        """
        Create relationships between claim and entities

        Creates:
        - Entity (subject) -[:MAKES_CLAIM]-> Claim
        - Claim -[:ABOUT]-> Entity (object) [if object exists]

        Args:
            claim_id: Claim ID
            subject_entity_name: Subject entity name
            object_entity_name: Object entity name (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.get_session()

            # Helper function to find entity with fuzzy matching
            def find_entity_fuzzy(entity_name: str) -> Optional[str]:
                """
                Find entity using fuzzy matching strategies:
                1. Exact match
                2. Case-insensitive match
                3. Match without parentheses content (e.g., "NAME (ENGLISH)" -> "NAME")
                4. Match with parentheses content stripped from both sides
                """
                # Strategy 1: Exact match
                query_exact = """
                MATCH (e:Entity {name: $name})
                RETURN e.name AS matched_name
                LIMIT 1
                """
                result = session.run(query_exact, name=entity_name)
                records = list(result)
                if records:
                    return records[0]["matched_name"]

                # Strategy 2: Case-insensitive match
                query_case_insensitive = """
                MATCH (e:Entity)
                WHERE toLower(e.name) = toLower($name)
                RETURN e.name AS matched_name
                LIMIT 1
                """
                result = session.run(query_case_insensitive, name=entity_name)
                records = list(result)
                if records:
                    return records[0]["matched_name"]

                # Strategy 3: Strip parentheses from search term and try matching
                # e.g., "THỬ NGHIỆM CÓ KIỂM SOÁT (REGULATORY SANDBOX)" -> "THỬ NGHIỆM CÓ KIỂM SOÁT"
                import re
                name_without_parens = re.sub(r'\s*\([^)]*\)\s*', '', entity_name).strip()
                if name_without_parens != entity_name:
                    query_no_parens = """
                    MATCH (e:Entity)
                    WHERE e.name = $name OR e.name STARTS WITH $name_prefix
                    RETURN e.name AS matched_name
                    LIMIT 1
                    """
                    result = session.run(
                        query_no_parens,
                        name=name_without_parens,
                        name_prefix=name_without_parens
                    )
                    records = list(result)
                    if records:
                        return records[0]["matched_name"]

                # Strategy 4: Match by stripping parentheses from database entities
                query_db_no_parens = """
                MATCH (e:Entity)
                WITH e,
                     replace(replace(e.name, '(', ''), ')', '') AS cleaned_name
                WHERE cleaned_name CONTAINS $search_term OR $search_term CONTAINS cleaned_name
                RETURN e.name AS matched_name
                ORDER BY size(e.name) ASC
                LIMIT 1
                """
                result = session.run(query_db_no_parens, search_term=name_without_parens)
                records = list(result)
                if records:
                    return records[0]["matched_name"]

                return None

            # Find subject entity using fuzzy matching
            matched_subject = find_entity_fuzzy(subject_entity_name)

            if not matched_subject:
                logger.warning(f"Failed to link subject entity {subject_entity_name} to claim")
                return False

            # Link subject entity to claim (MAKES_CLAIM)
            query_subject = """
            MATCH (c:Claim {id: $claim_id})
            MATCH (e:Entity {name: $entity_name})
            MERGE (e)-[r:MAKES_CLAIM]->(c)
            ON CREATE SET r.created_at = datetime()
            RETURN r
            """

            result = session.run(
                query_subject,
                claim_id=claim_id,
                entity_name=matched_subject,
            )

            records = list(result)
            if not records:
                logger.warning(f"Failed to create MAKES_CLAIM relationship for {matched_subject}")
                return False

            # Link claim to object entity (ABOUT) if object exists and is not NONE
            if object_entity_name and object_entity_name.upper() != "NONE":
                matched_object = find_entity_fuzzy(object_entity_name)

                if matched_object:
                    query_object = """
                    MATCH (c:Claim {id: $claim_id})
                    MATCH (e:Entity {name: $entity_name})
                    MERGE (c)-[r:ABOUT]->(e)
                    ON CREATE SET r.created_at = datetime()
                    RETURN r
                    """

                    session.run(
                        query_object,
                        claim_id=claim_id,
                        entity_name=matched_object,
                    )
                else:
                    logger.debug(f"Object entity {object_entity_name} not found (optional)")

            return True

        except Exception as e:
            logger.error(f"Claim-entity linking error: {e}")
            return False

    def link_claim_to_textunit(
        self,
        claim_id: str,
        textunit_id: str,
    ) -> bool:
        """
        Create SOURCED_FROM relationship between claim and text unit

        Args:
            claim_id: Claim ID
            textunit_id: TextUnit ID

        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.get_session()

            query = """
            MATCH (c:Claim {id: $claim_id})
            MATCH (t:TextUnit {id: $textunit_id})
            MERGE (c)-[r:SOURCED_FROM]->(t)
            ON CREATE SET r.created_at = datetime()
            RETURN r
            """

            result = session.run(
                query,
                claim_id=claim_id,
                textunit_id=textunit_id,
            )

            return result.single() is not None

        except Exception as e:
            logger.error(f"Claim-TextUnit linking error: {e}")
            return False

    def get_claims_for_entity(
        self,
        entity_name: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Get all claims related to an entity (as subject or object)

        Args:
            entity_name: Entity name
            limit: Maximum number of claims to return

        Returns:
            List of claim dictionaries
        """
        try:
            session = self.get_session()

            query = """
            MATCH (e:Entity {name: $entity_name})
            MATCH (c:Claim)
            WHERE (e)-[:MAKES_CLAIM]->(c) OR (c)-[:ABOUT]->(e)
            OPTIONAL MATCH (c)-[:SOURCED_FROM]->(t:TextUnit)
            RETURN c, t.text as source_text
            LIMIT $limit
            """

            result = session.run(
                query,
                entity_name=entity_name,
                limit=limit,
            )

            claims = []
            for record in result:
                claim_node = record["c"]
                claims.append({
                    "id": claim_node["id"],
                    "subject": claim_node["subject"],
                    "object": claim_node["object"],
                    "claim_type": claim_node["claim_type"],
                    "status": claim_node["status"],
                    "description": claim_node["description"],
                    "start_date": claim_node.get("start_date"),
                    "end_date": claim_node.get("end_date"),
                    "source_text": record.get("source_text") or claim_node.get("source_text", ""),
                    "created_at": str(claim_node.get("created_at", "")),
                })

            return claims

        except Exception as e:
            logger.error(f"Get claims error: {e}")
            return []

    def get_all_claims(
        self,
        claim_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get all claims in the graph with optional filters

        Args:
            claim_type: Filter by claim type (optional)
            status: Filter by status (optional)
            limit: Maximum number of claims to return

        Returns:
            List of claim dictionaries
        """
        try:
            session = self.get_session()

            # Build query with optional filters
            where_clauses = []
            params = {"limit": limit}

            if claim_type:
                where_clauses.append("c.claim_type = $claim_type")
                params["claim_type"] = claim_type

            if status:
                where_clauses.append("c.status = $status")
                params["status"] = status

            where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"

            query = f"""
            MATCH (c:Claim)
            WHERE {where_clause}
            OPTIONAL MATCH (c)-[:SOURCED_FROM]->(t:TextUnit)
            RETURN c, t.text as source_text
            LIMIT $limit
            """

            result = session.run(query, **params)

            claims = []
            for record in result:
                claim_node = record["c"]
                claims.append({
                    "id": claim_node["id"],
                    "subject": claim_node["subject"],
                    "object": claim_node["object"],
                    "claim_type": claim_node["claim_type"],
                    "status": claim_node["status"],
                    "description": claim_node["description"],
                    "start_date": claim_node.get("start_date"),
                    "end_date": claim_node.get("end_date"),
                    "source_text": record.get("source_text") or claim_node.get("source_text", ""),
                    "created_at": str(claim_node.get("created_at", "")),
                })

            return claims

        except Exception as e:
            logger.error(f"Get all claims error: {e}")
            return []

    def get_affected_communities_for_document(
        self,
        document_id: str,
    ) -> Dict[str, Any]:
        """
        Get all communities affected by a document update
        Used for incremental community detection

        Args:
            document_id: Document ID

        Returns:
            Dictionary with affected communities and entities
        """
        try:
            session = self.get_session()

            query = """
            MATCH (d:Document {id: $document_id})<-[:PART_OF]-(t:TextUnit)
            <-[:MENTIONED_IN]-(e:Entity)-[:IN_COMMUNITY]->(c:Community)
            RETURN
                COLLECT(DISTINCT c.id) AS community_ids,
                COLLECT(DISTINCT e.id) AS entity_ids,
                COUNT(DISTINCT c) AS num_communities,
                COUNT(DISTINCT e) AS num_entities
            """

            result = session.run(query, document_id=document_id).single()

            if result:
                return {
                    "community_ids": result["community_ids"],
                    "affected_entities": result["entity_ids"],
                    "num_communities": result["num_communities"],
                    "num_entities": result["num_entities"],
                }

            return {
                "community_ids": [],
                "affected_entities": [],
                "num_communities": 0,
                "num_entities": 0,
            }

        except Exception as e:
            logger.error(f"Error getting affected communities: {e}")
            return {
                "community_ids": [],
                "affected_entities": [],
                "num_communities": 0,
                "num_entities": 0,
            }

    def delete_document_graph_data(
        self,
        document_id: str,
    ) -> Dict[str, Any]:
        """
        Delete all graph data associated with a document
        Used for incremental updates to clean old data before reprocessing

        This includes:
        - TextUnit nodes and their relationships
        - Claims sourced from this document
        - Orphaned entities (entities only mentioned in this document)

        Args:
            document_id: Document ID

        Returns:
            Dictionary with deletion statistics
        """
        try:
            session = self.get_session()

            # Step 1: Delete claims sourced from this document's text units
            claims_query = """
            MATCH (d:Document {id: $document_id})<-[:PART_OF]-(t:TextUnit)
            <-[:SOURCED_FROM]-(c:Claim)
            DETACH DELETE c
            RETURN COUNT(c) AS claims_deleted
            """
            claims_result = session.run(claims_query, document_id=document_id).single()
            claims_deleted = claims_result["claims_deleted"] if claims_result else 0

            # Step 2: Get entities that will become orphaned (only mentioned in this document)
            orphan_query = """
            MATCH (d:Document {id: $document_id})<-[:PART_OF]-(t:TextUnit)
            <-[:MENTIONED_IN]-(e:Entity)
            WHERE NOT EXISTS {
                MATCH (e)-[:MENTIONED_IN]->(other_t:TextUnit)-[:PART_OF]->(:Document)
                WHERE other_t.document_id <> $document_id
            }
            RETURN COLLECT(e.id) AS orphan_entity_ids, COUNT(e) AS orphan_count
            """
            orphan_result = session.run(orphan_query, document_id=document_id).single()
            orphan_entity_ids = orphan_result["orphan_entity_ids"] if orphan_result else []
            orphan_count = orphan_result["orphan_count"] if orphan_result else 0

            # Step 3: Delete orphaned entities and their relationships
            if orphan_entity_ids:
                delete_orphans_query = """
                MATCH (e:Entity)
                WHERE e.id IN $orphan_ids
                DETACH DELETE e
                RETURN COUNT(e) AS entities_deleted
                """
                orphans_result = session.run(
                    delete_orphans_query,
                    orphan_ids=orphan_entity_ids
                ).single()
                entities_deleted = orphans_result["entities_deleted"] if orphans_result else 0
            else:
                entities_deleted = 0

            # Step 4: For non-orphaned entities, just remove the MENTIONED_IN relationships
            # to this document's text units and decrement mention_count
            update_entities_query = """
            MATCH (d:Document {id: $document_id})<-[:PART_OF]-(t:TextUnit)
            <-[r:MENTIONED_IN]-(e:Entity)
            WHERE NOT e.id IN $orphan_ids
            DELETE r
            WITH e
            SET e.mention_count = CASE
                WHEN e.mention_count > 1 THEN e.mention_count - 1
                ELSE 1
            END
            RETURN COUNT(DISTINCT e) AS entities_updated
            """
            update_result = session.run(
                update_entities_query,
                document_id=document_id,
                orphan_ids=orphan_entity_ids
            ).single()
            entities_updated = update_result["entities_updated"] if update_result else 0

            # Step 5: Delete TextUnit nodes (this will also delete PART_OF relationships)
            textunits_query = """
            MATCH (d:Document {id: $document_id})<-[:PART_OF]-(t:TextUnit)
            DETACH DELETE t
            RETURN COUNT(t) AS textunits_deleted
            """
            textunits_result = session.run(textunits_query, document_id=document_id).single()
            textunits_deleted = textunits_result["textunits_deleted"] if textunits_result else 0

            logger.info(
                f"✅ Deleted graph data for document {document_id}: "
                f"{textunits_deleted} text units, {entities_deleted} orphaned entities, "
                f"{entities_updated} entities updated, {claims_deleted} claims"
            )

            return {
                "status": "success",
                "textunits_deleted": textunits_deleted,
                "entities_deleted": entities_deleted,
                "entities_affected": entities_updated + entities_deleted,
                "claims_deleted": claims_deleted,
            }

        except Exception as e:
            logger.error(f"Error deleting document graph data: {e}")
            return {
                "status": "error",
                "message": str(e),
                "textunits_deleted": 0,
                "entities_deleted": 0,
                "entities_affected": 0,
                "claims_deleted": 0,
            }

    def update_entity(
        self,
        entity_id: str,
        name: Optional[str] = None,
        entity_type: Optional[str] = None,
        description: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> bool:
        """
        Update an existing entity node
        Used for incremental updates instead of recreating entities

        Args:
            entity_id: Entity ID to update
            name: New entity name (optional)
            entity_type: New entity type (optional)
            description: New description (optional)
            confidence: New confidence score (optional)

        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.get_session()

            # Build SET clause dynamically based on provided parameters
            set_clauses = ["e.updated_at = datetime()"]
            params = {"entity_id": entity_id}

            if name is not None:
                set_clauses.append("e.name = $name")
                params["name"] = name

            if entity_type is not None:
                set_clauses.append("e.type = $entity_type")
                params["entity_type"] = entity_type

            if description is not None:
                set_clauses.append("e.description = $description")
                params["description"] = description

            if confidence is not None:
                set_clauses.append(
                    "e.confidence = CASE WHEN $confidence > e.confidence THEN $confidence ELSE e.confidence END"
                )
                params["confidence"] = confidence

            query = f"""
            MATCH (e:Entity {{id: $entity_id}})
            SET {', '.join(set_clauses)}
            RETURN e.id as id
            """

            result = session.run(query, **params)

            if result.single():
                logger.info(f"Updated entity {entity_id}")
                return True

            logger.warning(f"Entity {entity_id} not found for update")
            return False

        except Exception as e:
            logger.error(f"Entity update error: {e}")
            return False

    def update_document_node_status(
        self,
        document_id: str,
        status: str,
    ) -> bool:
        """
        Update document node status in Neo4j

        Args:
            document_id: Document ID
            status: New status (pending, processing, completed, failed)

        Returns:
            True if successful, False otherwise
        """
        try:
            session = self.get_session()

            query = """
            MATCH (d:Document {id: $document_id})
            SET d.status = $status,
                d.updated_at = datetime()
            RETURN d.id as id
            """

            result = session.run(
                query,
                document_id=document_id,
                status=status,
            )

            return result.single() is not None

        except Exception as e:
            logger.error(f"Document status update error: {e}")
            return False

    def close(self):
        """Close graph session"""
        if self.session:
            self.session.close()
            self.session = None


# Export singleton instance
graph_service = GraphService()
