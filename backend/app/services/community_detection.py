"""
Community detection service using Neo4j GDS Leiden algorithm
Identifies clusters of related entities in the knowledge graph
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.db.neo4j import get_neo4j_session

logger = logging.getLogger(__name__)


class CommunityDetectionService:
    """Service for community detection using Leiden algorithm via Neo4j GDS"""

    def __init__(self):
        """Initialize community detection service"""
        self.session = None

    def get_session(self):
        """Get or create Neo4j session"""
        if not self.session:
            self.session = get_neo4j_session()
        return self.session

    def init_gds_graph(self) -> bool:
        """
        Initialize GDS graph projection for community detection

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            session = self.get_session()

            # Drop existing graph if present
            drop_query = """
            CALL gds.graph.list()
            YIELD graphName
            WHERE graphName = 'entity_graph'
            CALL gds.graph.drop(graphName)
            YIELD graphName AS dropped
            RETURN dropped
            """

            session.run(drop_query)
            logger.info("Dropped existing GDS graph projection")

            # Create graph projection for entity relationships
            projection_query = """
            CALL gds.graph.project(
                'entity_graph',
                'Entity',
                {
                    RELATED_TO: {},
                    MENTIONED_IN: {orientation: 'UNDIRECTED'},
                    PART_OF: {orientation: 'UNDIRECTED'}
                },
                {
                    relationshipProperties: ['weight']
                }
            )
            YIELD graphName, nodeCount, relationshipCount, projectMillis
            RETURN graphName, nodeCount, relationshipCount, projectMillis
            """

            result = session.run(projection_query).single()

            if result:
                logger.info(
                    f"GDS graph projected: {result['graphName']} "
                    f"({result['nodeCount']} nodes, {result['relationshipCount']} rels)"
                )
                return True
            return False

        except Exception as e:
            logger.error(f"Failed to initialize GDS graph: {str(e)}")
            return False

    def detect_communities(
        self,
        seed: int = 42,
        include_intermediate_communities: bool = True,
        tolerance: float = 0.0001,
        max_iterations: int = 10,
    ) -> Dict[str, Any]:
        """
        Detect communities using Leiden algorithm

        Args:
            seed: Random seed for reproducibility
            include_intermediate_communities: Include intermediate community assignments
            tolerance: Tolerance threshold for convergence
            max_iterations: Maximum algorithm iterations

        Returns:
            Dictionary with community detection results
        """
        try:
            session = self.get_session()

            # Ensure graph projection exists
            list_result = session.run(
                "CALL gds.graph.list() YIELD graphName WHERE graphName = 'entity_graph' RETURN graphName"
            ).single()

            if not list_result:
                self.init_gds_graph()

            # Run Leiden algorithm
            leiden_query = """
            CALL gds.leiden.stream(
                'entity_graph',
                {
                    seed: $seed,
                    includeIntermediateCommunities: $include_intermediate,
                    tolerance: $tolerance,
                    maxIterations: $max_iterations,
                    concurrency: 4
                }
            )
            YIELD nodeId, communityId, intermediateCommunityIds
            WITH gds.util.asNode(nodeId) AS node, communityId, intermediateCommunityIds
            RETURN node.name AS entity_name, communityId, intermediateCommunityIds
            ORDER BY communityId
            """

            results = session.run(
                leiden_query,
                {
                    "seed": seed,
                    "include_intermediate": include_intermediate_communities,
                    "tolerance": tolerance,
                    "max_iterations": max_iterations,
                },
            ).data()

            # Organize by community
            communities = {}
            for record in results:
                comm_id = record["communityId"]
                if comm_id not in communities:
                    communities[comm_id] = {
                        "id": comm_id,
                        "entities": [],
                        "size": 0,
                    }
                communities[comm_id]["entities"].append(record["entity_name"])
                communities[comm_id]["size"] += 1

            # Store community assignments in Neo4j
            self._store_community_assignments(session, results)

            logger.info(f"Detected {len(communities)} communities")
            return {
                "status": "success",
                "num_communities": len(communities),
                "communities": communities,
            }

        except Exception as e:
            logger.error(f"Community detection failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _store_community_assignments(
        self, session, results: List[Dict]
    ) -> None:
        """
        Store community assignments in Neo4j

        Args:
            session: Neo4j session
            results: Community detection results
        """
        try:
            # Create Community nodes and relationships
            for record in results:
                entity_name = record["entity_name"]
                community_id = record["communityId"]

                store_query = """
                MATCH (e:Entity {name: $entity_name})
                MERGE (c:Community {id: $community_id})
                ON CREATE SET c.createdAt = datetime()
                MERGE (e)-[r:IN_COMMUNITY]->(c)
                SET r.confidence = 0.95, r.timestamp = datetime()
                RETURN e.name, c.id
                """

                session.run(
                    store_query,
                    {"entity_name": entity_name, "community_id": community_id},
                )

            logger.info("Community assignments stored in Neo4j")

        except Exception as e:
            logger.error(f"Failed to store community assignments: {str(e)}")

    def get_community_members(self, community_id: int) -> Dict[str, Any]:
        """
        Get all members of a specific community

        Args:
            community_id: Community ID

        Returns:
            Dictionary with community members and statistics
        """
        try:
            session = self.get_session()

            query = """
            MATCH (c:Community {id: $community_id})<-[r:IN_COMMUNITY]-(e:Entity)
            OPTIONAL MATCH (e)-[rel]-(other_e:Entity)
            WHERE other_e.name IN [en.name | en in collect(other_e)]
            RETURN
                c.id AS community_id,
                collect(e.name) AS members,
                count(DISTINCT rel) AS internal_relationships,
                count(DISTINCT e) AS member_count
            LIMIT 1
            """

            result = session.run(query, {"community_id": community_id}).single()

            if result:
                return {
                    "status": "success",
                    "community_id": result["community_id"],
                    "members": result["members"],
                    "member_count": result["member_count"],
                    "internal_relationships": result["internal_relationships"],
                }

            return {"status": "not_found", "community_id": community_id}

        except Exception as e:
            logger.error(f"Failed to get community members: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_community_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about all detected communities

        Returns:
            Dictionary with community statistics
        """
        try:
            session = self.get_session()

            query = """
            MATCH (c:Community)
            WITH c
            OPTIONAL MATCH (e:Entity)-[r:IN_COMMUNITY]->(c)
            RETURN
                count(DISTINCT c) AS num_communities,
                count(DISTINCT e) AS total_members,
                collect({
                    id: c.id,
                    size: count(DISTINCT e)
                }) AS community_sizes
            """

            result = session.run(query).single()

            if result and result["num_communities"] > 0:
                return {
                    "status": "success",
                    "num_communities": result["num_communities"],
                    "total_members": result["total_members"],
                    "community_sizes": result["community_sizes"],
                    "avg_community_size": (
                        result["total_members"] / result["num_communities"]
                        if result["num_communities"] > 0
                        else 0
                    ),
                }

            return {
                "status": "no_communities",
                "num_communities": 0,
                "message": "No communities detected yet",
            }

        except Exception as e:
            logger.error(f"Failed to get community statistics: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_entities_in_community_path(
        self, source_entity: str, target_entity: str, max_depth: int = 3
    ) -> Dict[str, Any]:
        """
        Find path between two entities considering community structure

        Args:
            source_entity: Source entity name
            target_entity: Target entity name
            max_depth: Maximum path depth to explore

        Returns:
            Dictionary with path information
        """
        try:
            session = self.get_session()

            # First check if entities are in the same community
            query = """
            MATCH (source:Entity {name: $source})-[r1:IN_COMMUNITY]->(c:Community)
            MATCH (target:Entity {name: $target})-[r2:IN_COMMUNITY]->(c)
            WITH source, target, c, [r in relationships(source, target) WHERE type(r) IN ['RELATED_TO', 'MENTIONED_IN']] AS paths
            RETURN
                c.id AS community_id,
                source.name AS source_entity,
                target.name AS target_entity,
                size(paths) AS direct_connections,
                'same_community' AS path_type
            LIMIT 1
            """

            result = session.run(
                query, {"source": source_entity, "target": target_entity}
            ).single()

            if result:
                return {
                    "status": "success",
                    "path_type": result["path_type"],
                    "community_id": result["community_id"],
                    "source": result["source_entity"],
                    "target": result["target_entity"],
                    "direct_connections": result["direct_connections"],
                }

            # If not in same community, find cross-community path
            cross_query = """
            MATCH path = (source:Entity {name: $source})-[*1..{max_depth}]-(target:Entity {name: $target})
            WHERE all(rel in relationships(path) WHERE type(rel) IN ['RELATED_TO', 'MENTIONED_IN', 'PART_OF'])
            WITH [n in nodes(path) | n.name] AS entity_path,
                 length(path) AS path_length
            RETURN entity_path, path_length
            ORDER BY path_length
            LIMIT 1
            """.format(
                max_depth=max_depth
            )

            result = session.run(
                cross_query, {"source": source_entity, "target": target_entity}
            ).single()

            if result:
                return {
                    "status": "success",
                    "path_type": "cross_community",
                    "path": result["entity_path"],
                    "length": result["path_length"],
                }

            return {
                "status": "not_found",
                "source": source_entity,
                "target": target_entity,
            }

        except Exception as e:
            logger.error(f"Failed to find community path: {str(e)}")
            return {"status": "error", "message": str(e)}


# Singleton instance
community_detection_service = CommunityDetectionService()
