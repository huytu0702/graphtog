"""
Neo4j graph database connection and schema management
"""

from typing import Optional

from neo4j import GraphDatabase, Session as Neo4jSession

from app.config import get_settings


class Neo4jConnection:
    """Neo4j database connection manager"""

    _instance: Optional["Neo4jConnection"] = None
    _driver = None

    def __new__(cls):
        """Singleton pattern - ensure only one connection instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Neo4j connection"""
        if self._driver is None:
            settings = get_settings()
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
                max_connection_pool_size=100,  # Increased from default 100 to handle concurrent requests
                connection_acquisition_timeout=120.0,  # Increased from 60s to 120s
            )

    def get_session(self) -> Neo4jSession:
        """Get a Neo4j session"""
        return self._driver.session()

    def close(self):
        """Close Neo4j connection"""
        if self._driver is not None:
            self._driver.close()

    def init_schema(self):
        """Initialize graph schema with constraints and indexes"""
        session = self.get_session()
        try:
            # Create constraints
            session.run(
                "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE"
            )
            session.run(
                "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE"
            )

            # Create indexes
            session.run("CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)")
            session.run("CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)")
            session.run("CREATE INDEX document_name IF NOT EXISTS FOR (d:Document) ON (d.name)")
            session.run(
                "CREATE INDEX sentence_id IF NOT EXISTS FOR (s:Sentence) ON (s.sentence_id)"
            )

            print("✅ Neo4j schema initialized successfully")
        except Exception as e:
            print(f"⚠️ Neo4j schema initialization warning: {str(e)}")
        finally:
            session.close()


# Global Neo4j connection instance
_neo4j_connection: Optional[Neo4jConnection] = None


def get_neo4j_connection() -> Neo4jConnection:
    """Get Neo4j connection singleton"""
    global _neo4j_connection
    if _neo4j_connection is None:
        _neo4j_connection = Neo4jConnection()
    return _neo4j_connection


def get_neo4j_session() -> Neo4jSession:
    """Get a Neo4j session for queries"""
    return get_neo4j_connection().get_session()


def init_neo4j() -> None:
    """Initialize Neo4j connection and schema"""
    connection = get_neo4j_connection()
    connection.init_schema()


def close_neo4j() -> None:
    """Close Neo4j connection"""
    global _neo4j_connection
    if _neo4j_connection is not None:
        _neo4j_connection.close()
        _neo4j_connection = None
