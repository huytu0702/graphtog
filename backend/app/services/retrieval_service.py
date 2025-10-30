"""
Multi-level retrieval service for hierarchical search
Implements Local, Community, and Global retrieval strategies
"""

import logging
from typing import Any, Dict, List, Optional

from app.db.neo4j import get_neo4j_session
from app.services.community_detection import community_detection_service
from app.services.graph_service import graph_service
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class MultiLevelRetrievalService:
    """Service for multi-level hierarchical retrieval"""

    def __init__(self):
        """Initialize retrieval service"""
        self.session = None

    def get_session(self):
        """Get or create Neo4j session"""
        if not self.session:
            self.session = get_neo4j_session()
        return self.session

    def retrieve_local_context(
        self, 
        query_entity: str, 
        hop_limit: int = 1,
        include_text: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve local context around a query entity following Microsoft GraphRAG methodology
        
        Microsoft GraphRAG local search requires:
        1. Related entities via graph traversal
        2. Actual text units (document chunks) for context
        3. Relationship details

        Args:
            query_entity: Entity name to search around
            hop_limit: Number of hops to traverse (default 1 per GraphRAG)
            include_text: Whether to include text units (strongly recommended)

        Returns:
            Dictionary with local context including entities, relationships, and text
        """
        try:
            session = self.get_session()

            # Find the entity and related entities via semantic relationships
            # Exclude IN_COMMUNITY to focus on actual content relationships
            query = f"""
            MATCH (source:Entity {{name: $entity}})
            
            // Get semantically related entities (not just community membership)
            OPTIONAL MATCH (source)-[r:RELATED_TO|SUPPORTS|CAUSES|OPPOSES|MENTIONS|CONTAINS|PRECEDES|REQUIRED*1..{hop_limit}]-(neighbor:Entity)
            
            WITH source, 
                 COLLECT(DISTINCT {{
                     name: neighbor.name,
                     type: neighbor.type,
                     description: neighbor.description,
                     id: neighbor.id
                 }}) AS neighbors,
                 COLLECT(DISTINCT type(r)) AS relationship_types
            
            RETURN
                source.id AS source_id,
                source.name AS source_entity,
                source.type AS source_type,
                source.description AS source_description,
                [n IN neighbors WHERE n.name IS NOT NULL] AS neighbors,
                relationship_types
            """

            result = session.run(query, {"entity": query_entity}).single()

            if not result:
                return {"status": "not_found", "entity": query_entity}

            data = result.data()
            response = {
                "status": "success",
                "retrieval_type": "local",
                "source_entity": data.get("source_entity"),
                "source_id": data.get("source_id"),
                "source_type": data.get("source_type"),
                "source_description": data.get("source_description"),
                "neighbor_count": len(data.get("neighbors", [])),
                "neighbors": data.get("neighbors", [])[:15],
                "relationship_types": [rt for rt in data.get("relationship_types", []) if rt],
            }
            
            # Retrieve text units for the source entity (Microsoft GraphRAG requirement)
            if include_text and data.get("source_id"):
                text_query = """
                MATCH (e:Entity {id: $entity_id})-[:MENTIONED_IN]->(t:TextUnit)
                RETURN 
                    t.id AS text_unit_id,
                    t.text AS text,
                    t.document_id AS document_id,
                    t.start_char AS start_char
                ORDER BY t.start_char
                LIMIT 10
                """
                
                text_results = session.run(text_query, entity_id=data.get("source_id"))
                text_units = []
                
                for text_record in text_results:
                    text_data = text_record.data()
                    text_units.append({
                        "text_unit_id": text_data.get("text_unit_id"),
                        "text": text_data.get("text"),
                        "document_id": text_data.get("document_id"),
                    })
                
                response["text_units"] = text_units
                logger.info(f"Retrieved {len(text_units)} text units for local search on '{query_entity}'")

            return response

        except Exception as e:
            logger.error(f"Local retrieval failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def retrieve_community_context(
        self, query_entity: str, include_summaries: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve community context for a query entity

        Args:
            query_entity: Entity name to search around
            include_summaries: Whether to include community summaries

        Returns:
            Dictionary with community context
        """
        try:
            session = self.get_session()

            # Find communities containing the entity
            query = """
            MATCH (e:Entity {name: $entity})-[r:IN_COMMUNITY]->(c:Community)
            WITH c, e
            MATCH (other_e:Entity)-[r2:IN_COMMUNITY]->(c)
            RETURN
                c.id AS community_id,
                e.name AS query_entity,
                collect(DISTINCT other_e.name) AS community_members,
                c.summary AS summary,
                c.key_themes AS themes
            """

            result = session.run(query, {"entity": query_entity}).single()

            if not result:
                return {"status": "not_in_community", "entity": query_entity}

            return {
                "status": "success",
                "retrieval_type": "community",
                "community_id": result["community_id"],
                "query_entity": query_entity,
                "community_size": len(result["community_members"]),
                "members": result["community_members"][:20],
                "summary": result["summary"] if include_summaries else None,
                "themes": (result["themes"].split(",") if result["themes"] else []),
            }

        except Exception as e:
            logger.error(f"Community retrieval failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def retrieve_global_context(self, use_summaries: bool = True) -> Dict[str, Any]:
        """
        Retrieve global context (all communities summary) with Microsoft GraphRAG methodology
        
        Args:
            use_summaries: Whether to include generated summaries
            
        Returns:
            Dictionary with global context including summaries, themes, and significance
        """
        try:
            session = self.get_session()

            # Query communities with their summaries - focus on base level (level 0)
            query = """
            MATCH (c:Community)
            WHERE c.level = 0  # Only base-level communities for global search
            WITH c
            OPTIONAL MATCH (e:Entity)-[r:IN_COMMUNITY]->(c)
            RETURN
                collect({
                    community_id: c.id,
                    level: COALESCE(c.level, 0),
                    size: count(DISTINCT e),
                    summary: COALESCE(c.summary, ""),
                    themes: COALESCE(c.key_themes, ""),
                    significance: COALESCE(c.significance, "medium"),
                    created_at: c.createdAt
                }) AS communities,
                count(DISTINCT c) AS num_communities,
                count(DISTINCT e) AS total_entities
            """

            result = session.run(query).single()

            if not result or result["num_communities"] == 0:
                return {
                    "status": "no_communities",
                    "message": "No communities found",
                }

            communities = result["communities"]
            
            # Filter communities with summaries if requested
            if use_summaries:
                communities_with_summaries = [
                    c for c in communities if c.get("summary") and c["summary"].strip()
                ]
                if not communities_with_summaries:
                    logger.warning("No community summaries found, using raw communities")
                else:
                    communities = communities_with_summaries
                    logger.info(f"Found {len(communities)} communities with summaries")
            
            # Sort by size (importance)
            communities = sorted(communities, key=lambda x: x.get("size", 0), reverse=True)

            return {
                "status": "success",
                "retrieval_type": "global",
                "num_communities": len(communities),
                "total_entities": result["total_entities"],
                "communities": communities,
                "summaries_available": all(c.get("summary") and c["summary"].strip() for c in communities),
            }

        except Exception as e:
            logger.error(f"Global retrieval failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def hierarchical_search(
        self,
        query: str,
        retrieval_levels: List[str] = None,
        combine_results: bool = True,
    ) -> Dict[str, Any]:
        """
        Perform hierarchical search combining multiple retrieval levels

        Args:
            query: Query string
            retrieval_levels: List of levels to use ['local', 'community', 'global']
            combine_results: Whether to combine results from all levels

        Returns:
            Dictionary with combined retrieval results
        """
        try:
            if retrieval_levels is None:
                retrieval_levels = ["local", "community", "global"]

            session = self.get_session()

            # Extract entities from query
            query_entities = llm_service.extract_entities(query)

            if not query_entities or query_entities["status"] != "success":
                return {"status": "error", "message": "Could not extract query entities"}

            results = {
                "status": "success",
                "query": query,
                "retrieval_levels": retrieval_levels,
                "query_entities": query_entities.get("entities", [])[:3],
                "results": {},
            }

            # Local retrieval
            if "local" in retrieval_levels:
                local_results = []
                for entity in query_entities.get("entities", [])[:3]:
                    local_result = self.retrieve_local_context(entity.get("name"), hop_limit=1)
                    if local_result["status"] == "success":
                        local_results.append(local_result)
                results["results"]["local"] = local_results

            # Community retrieval
            if "community" in retrieval_levels:
                community_results = []
                for entity in query_entities.get("entities", [])[:3]:
                    community_result = self.retrieve_community_context(entity.get("name"))
                    if community_result["status"] == "success":
                        community_results.append(community_result)
                results["results"]["community"] = community_results

            # Global retrieval
            if "global" in retrieval_levels:
                global_result = self.retrieve_global_context()
                if global_result["status"] == "success":
                    results["results"]["global"] = global_result

            # Combine and rank results if requested
            if combine_results:
                results["combined"] = self._combine_retrieval_results(results)

            return results

        except Exception as e:
            logger.error(f"Hierarchical search failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _combine_retrieval_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine and rank results from multiple retrieval levels

        Args:
            results: Results dictionary from hierarchical_search

        Returns:
            Combined and ranked results
        """
        combined = {
            "entities": set(),
            "communities": set(),
            "context_snippets": [],
        }

        # Collect local entities
        for local_result in results.get("results", {}).get("local", []):
            for neighbor in local_result.get("neighbors", []):
                combined["entities"].add(neighbor)

        # Collect community entities
        for community_result in results.get("results", {}).get("community", []):
            for member in community_result.get("members", []):
                combined["entities"].add(member)
            combined["communities"].add(community_result.get("community_id"))

        return {
            "entity_count": len(combined["entities"]),
            "entities": list(combined["entities"])[:30],
            "community_count": len(combined["communities"]),
            "communities": list(combined["communities"]),
        }

    def adaptive_retrieval(self, query: str, query_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Adaptively select retrieval strategy based on query type

        Args:
            query: User query
            query_type: Optional pre-classified query type

        Returns:
            Dictionary with adaptive retrieval results
        """
        try:
            # Classify query if not provided
            if not query_type:
                classification = llm_service.classify_query(query)
                query_type = classification.get("query_type", "exploratory")

            # Select retrieval strategy based on query type
            if query_type == "specific":
                # Use local retrieval for specific questions
                retrieval_levels = ["local"]
            elif query_type == "comparative":
                # Use community + local retrieval for comparative questions
                retrieval_levels = ["local", "community"]
            else:  # exploratory
                # Use all levels for exploratory questions
                retrieval_levels = ["local", "community", "global"]

            logger.info(
                f"Selected retrieval strategy: {retrieval_levels} for query type: {query_type}"
            )

            return self.hierarchical_search(query, retrieval_levels=retrieval_levels)

        except Exception as e:
            logger.error(f"Adaptive retrieval failed: {str(e)}")
            return {"status": "error", "message": str(e)}


# Singleton instance
retrieval_service = MultiLevelRetrievalService()
