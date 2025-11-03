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
                    RELATED_TO: {orientation: 'UNDIRECTED'},
                    MENTIONED_IN: {orientation: 'UNDIRECTED'}
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
                "CALL gds.graph.list() YIELD graphName WHERE graphName = 'entity_graph' RETURN graphName LIMIT 1"
            ).single()

            if not list_result:
                self.init_gds_graph()

            # Run Leiden algorithm
            leiden_query = """
            CALL gds.leiden.stream(
                'entity_graph',
                {
                    randomSeed: $seed,
                    includeIntermediateCommunities: $include_intermediate,
                    tolerance: $tolerance,
                    maxLevels: $max_iterations,
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

    def _store_community_assignments(self, session, results: List[Dict]) -> None:
        """
        Store community assignments in Neo4j with hierarchy levels

        Args:
            session: Neo4j session
            results: Community detection results with hierarchy info
        """
        try:
            # First pass: create all community nodes and relationships
            for record in results:
                entity_name = record["entity_name"]
                community_id = record["communityId"]
                community_level = 0  # Base level for primary community

                # Create primary community relationship
                store_query = """
                MATCH (e:Entity {name: $entity_name})
                MERGE (c:Community {id: $community_id})
                ON CREATE SET 
                    c.createdAt = datetime(),
                    c.level = $community_level,
                    c.summary = ""
                MERGE (e)-[r:IN_COMMUNITY]->(c)
                SET r.confidence = 0.95, 
                    r.timestamp = datetime(),
                    r.community_level = $community_level
                RETURN e.name, c.id
                """

                session.run(
                    store_query,
                    {
                        "entity_name": entity_name,
                        "community_id": community_id,
                        "community_level": community_level,
                    },
                )

                # Store intermediate communities (hierarchy)
                if "intermediateCommunityIds" in record and record["intermediateCommunityIds"]:
                    intermediate_ids = record["intermediateCommunityIds"]
                    for idx, inter_comm_id in enumerate(intermediate_ids):
                        level = idx + 1  # Higher level

                        # Create intermediate community node
                        inter_query = """
                        MATCH (e:Entity {name: $entity_name})
                        MERGE (ic:Community {id: $inter_community_id})
                        ON CREATE SET 
                            ic.createdAt = datetime(),
                            ic.level = $community_level,
                            ic.summary = ""
                        MERGE (e)-[r2:IN_COMMUNITY]->(ic)
                        SET r2.confidence = 0.85,
                            r2.timestamp = datetime(),
                            r2.community_level = $community_level
                        RETURN e.name, ic.id
                        """

                        session.run(
                            inter_query,
                            {
                                "entity_name": entity_name,
                                "inter_community_id": inter_comm_id,
                                "community_level": level,
                            },
                        )

            logger.info("✅ Community assignments stored with hierarchy levels")

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

            result = session.run(query, {"source": source_entity, "target": target_entity}).single()

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

    def detect_communities_incrementally(
        self,
        affected_entity_ids: List[str],
        seed: int = 42,
    ) -> Dict[str, Any]:
        """
        Perform incremental community detection for affected entities only
        More efficient than full recomputation for document updates

        Strategy:
        1. Remove old community assignments for affected entities
        2. Get neighboring entities (1-hop) that might be affected
        3. Run community detection on affected subgraph
        4. Update community assignments

        Args:
            affected_entity_ids: List of entity IDs that need community recomputation
            seed: Random seed for reproducibility

        Returns:
            Dictionary with incremental detection results
        """
        try:
            session = self.get_session()

            if not affected_entity_ids or len(affected_entity_ids) == 0:
                return {
                    "status": "success",
                    "message": "No affected entities, skipping incremental detection",
                    "communities_recomputed": 0,
                }

            logger.info(f"Starting incremental community detection for {len(affected_entity_ids)} entities...")

            # Step 1: Get old communities to mark as stale
            old_communities_query = """
            MATCH (e:Entity)-[:IN_COMMUNITY]->(c:Community)
            WHERE e.id IN $entity_ids
            RETURN COLLECT(DISTINCT c.id) AS old_community_ids
            """
            old_result = session.run(
                old_communities_query,
                entity_ids=affected_entity_ids
            ).single()
            old_community_ids = old_result["old_community_ids"] if old_result else []

            # Step 2: Remove old community assignments for affected entities
            remove_query = """
            MATCH (e:Entity)-[r:IN_COMMUNITY]->(:Community)
            WHERE e.id IN $entity_ids
            DELETE r
            RETURN COUNT(r) AS relationships_removed
            """
            remove_result = session.run(
                remove_query,
                entity_ids=affected_entity_ids
            ).single()
            relationships_removed = remove_result["relationships_removed"] if remove_result else 0

            logger.info(f"Removed {relationships_removed} old community assignments")

            # Step 3: Get expanded set of entities (affected + 1-hop neighbors)
            # This ensures community boundaries are properly recomputed
            expanded_entities_query = """
            MATCH (e:Entity)
            WHERE e.id IN $entity_ids

            // Get 1-hop neighbors
            OPTIONAL MATCH (e)-[r:RELATED_TO|MENTIONED_IN]-(neighbor:Entity)

            WITH COLLECT(DISTINCT e.id) + COLLECT(DISTINCT neighbor.id) AS all_entity_ids
            UNWIND all_entity_ids AS entity_id
            WITH DISTINCT entity_id
            WHERE entity_id IS NOT NULL

            RETURN COLLECT(entity_id) AS expanded_entity_ids
            """
            expanded_result = session.run(
                expanded_entities_query,
                entity_ids=affected_entity_ids
            ).single()
            expanded_entity_ids = expanded_result["expanded_entity_ids"] if expanded_result else affected_entity_ids

            logger.info(
                f"Expanded from {len(affected_entity_ids)} to {len(expanded_entity_ids)} entities "
                f"(including neighbors)"
            )

            # Step 4: Create temporary subgraph projection for affected entities
            subgraph_name = f"affected_subgraph_{seed}"

            # Drop existing subgraph if exists
            try:
                session.run(f"CALL gds.graph.drop('{subgraph_name}')")
            except:
                pass

            # Create subgraph projection
            subgraph_query = f"""
            CALL gds.graph.project.cypher(
                '{subgraph_name}',
                'MATCH (e:Entity) WHERE e.id IN $entity_ids RETURN id(e) AS id',
                'MATCH (e1:Entity)-[r:RELATED_TO|MENTIONED_IN]-(e2:Entity)
                 WHERE e1.id IN $entity_ids AND e2.id IN $entity_ids
                 RETURN id(e1) AS source, id(e2) AS target'
            )
            YIELD graphName, nodeCount, relationshipCount
            RETURN graphName, nodeCount, relationshipCount
            """

            subgraph_result = session.run(
                subgraph_query,
                entity_ids=expanded_entity_ids
            ).single()

            if not subgraph_result or subgraph_result["nodeCount"] == 0:
                logger.warning("No entities found for incremental community detection")
                return {
                    "status": "success",
                    "message": "No entities to process",
                    "communities_recomputed": 0,
                }

            logger.info(
                f"Created subgraph: {subgraph_result['nodeCount']} nodes, "
                f"{subgraph_result['relationshipCount']} relationships"
            )

            # Step 5: Run Leiden on subgraph
            leiden_query = f"""
            CALL gds.leiden.stream(
                '{subgraph_name}',
                {{
                    randomSeed: $seed,
                    includeIntermediateCommunities: false,
                    tolerance: 0.0001,
                    maxLevels: 10,
                    concurrency: 4
                }}
            )
            YIELD nodeId, communityId
            WITH gds.util.asNode(nodeId) AS node, communityId
            RETURN node.id AS entity_id, communityId
            """

            leiden_results = session.run(leiden_query, seed=seed).data()

            # Step 6: Store new community assignments
            communities_created = set()
            for result in leiden_results:
                entity_id = result["entity_id"]
                community_id = result["communityId"]
                communities_created.add(community_id)

                # Create/update community and relationship
                update_query = """
                MATCH (e:Entity {id: $entity_id})
                MERGE (c:Community {id: $community_id})
                ON CREATE SET
                    c.createdAt = datetime(),
                    c.level = 0,
                    c.summary = ""
                MERGE (e)-[r:IN_COMMUNITY]->(c)
                SET r.confidence = 0.95,
                    r.timestamp = datetime(),
                    r.community_level = 0
                """

                session.run(
                    update_query,
                    entity_id=entity_id,
                    community_id=community_id
                )

            # Step 7: Clean up subgraph
            try:
                session.run(f"CALL gds.graph.drop('{subgraph_name}')")
            except:
                pass

            # Step 8: Remove orphaned communities (communities with no members)
            cleanup_query = """
            MATCH (c:Community)
            WHERE NOT EXISTS((c)<-[:IN_COMMUNITY]-())
            DELETE c
            RETURN COUNT(c) AS orphaned_communities_removed
            """
            cleanup_result = session.run(cleanup_query).single()
            orphaned_removed = cleanup_result["orphaned_communities_removed"] if cleanup_result else 0

            if orphaned_removed > 0:
                logger.info(f"Removed {orphaned_removed} orphaned communities")

            logger.info(
                f"✅ Incremental community detection complete: "
                f"{len(communities_created)} communities created/updated"
            )

            return {
                "status": "success",
                "communities_recomputed": len(communities_created),
                "entities_processed": len(expanded_entity_ids),
                "old_communities_affected": len(old_community_ids),
                "orphaned_communities_removed": orphaned_removed,
            }

        except Exception as e:
            logger.error(f"Incremental community detection failed: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "communities_recomputed": 0,
            }


# Singleton instance
community_detection_service = CommunityDetectionService()
