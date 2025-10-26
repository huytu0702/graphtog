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
                document_id=document_id,
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
                document_id=document_id,
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

    def find_entity_by_name(self, name: str, entity_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
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
                """
                result = session.run(query, name=name, type=entity_type)
            else:
                query = """
                MATCH (e:Entity {name: $name})
                RETURN e.id as id, e.name as name, e.type as type, e.description as description, e.confidence as confidence
                """
                result = session.run(query, name=name)

            record = result.single()
            if record:
                return dict(record)
            return None

        except Exception as e:
            logger.error(f"Entity lookup error: {e}")
            return None

    def get_entity_context(
        self,
        entity_id: str,
        hop_limit: int = 2,
    ) -> Dict[str, Any]:
        """
        Get context around an entity (related entities and relationships)

        Args:
            entity_id: Entity to get context for
            hop_limit: How many hops to traverse

        Returns:
            Dict with entities and relationships
        """
        try:
            session = self.get_session()

            # Get entity and related entities
            query = """
            MATCH (e:Entity {id: $entity_id})
            MATCH path = (e)-[r*1..{hops}]-(related:Entity)
            RETURN DISTINCT
                e.id as central_entity_id,
                e.name as central_entity_name,
                COLLECT(DISTINCT {id: related.id, name: related.name, type: related.type}) as related_entities,
                COLLECT(DISTINCT {type: type(r), description: last(r).description}) as relationship_types
            """.format(hops=hop_limit)

            result = session.run(query, entity_id=entity_id)
            record = result.single()

            if record:
                return dict(record)
            return {}

        except Exception as e:
            logger.error(f"Context retrieval error: {e}")
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

    def close(self):
        """Close graph session"""
        if self.session:
            self.session.close()
            self.session = None


# Export singleton instance
graph_service = GraphService()
