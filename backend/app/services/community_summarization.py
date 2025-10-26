"""
Community summarization service
Generates summaries for each detected community using LLM
"""

import logging
from typing import Any, Dict, List, Optional

from app.db.neo4j import get_neo4j_session
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class CommunitySummarizationService:
    """Service for generating community summaries"""

    def __init__(self):
        """Initialize community summarization service"""
        self.session = None

    def get_session(self):
        """Get or create Neo4j session"""
        if not self.session:
            self.session = get_neo4j_session()
        return self.session

    def summarize_community(self, community_id: int) -> Dict[str, Any]:
        """
        Generate summary for a specific community

        Args:
            community_id: Community ID to summarize

        Returns:
            Dictionary with community summary
        """
        try:
            session = self.get_session()

            # Get community members and their relationships
            query = """
            MATCH (c:Community {id: $community_id})<-[r:IN_COMMUNITY]-(e:Entity)
            OPTIONAL MATCH (e)-[rel:RELATED_TO|MENTIONED_IN|PART_OF]-(other_e:Entity)
            WHERE (other_e)-[r2:IN_COMMUNITY]->(c)
            RETURN
                c.id AS community_id,
                collect(DISTINCT e.name) AS entities,
                collect(DISTINCT e.type) AS entity_types,
                collect({
                    source: e.name,
                    target: other_e.name,
                    type: type(rel),
                    description: rel.description
                }) AS relationships
            """

            result = session.run(query, {"community_id": community_id}).single()

            if not result:
                return {"status": "not_found", "community_id": community_id}

            entities = result["entities"]
            relationships = result["relationships"]

            # Generate context for LLM
            context = self._build_community_context(entities, relationships, result["entity_types"])

            # Generate summary using LLM
            summary_response = llm_service.generate_community_summary(context)

            # Store summary in Neo4j
            self._store_community_summary(session, community_id, summary_response)

            return {
                "status": "success",
                "community_id": community_id,
                "member_count": len(entities),
                "relationship_count": len(relationships),
                "summary": summary_response,
            }

        except Exception as e:
            logger.error(f"Failed to summarize community {community_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _build_community_context(
        self, entities: List[str], relationships: List[Dict], entity_types: List[str]
    ) -> str:
        """
        Build context string for LLM summarization

        Args:
            entities: List of entity names
            relationships: List of relationships
            entity_types: List of entity types

        Returns:
            Context string for LLM
        """
        context = "Community consisting of the following entities:\n\n"
        context += "ENTITIES:\n"
        for entity in entities[:20]:  # Limit to 20 entities
            context += f"- {entity}\n"

        if len(entities) > 20:
            context += f"- ... and {len(entities) - 20} more entities\n"

        context += "\nKEY RELATIONSHIPS:\n"
        for rel in relationships[:15]:  # Limit to 15 relationships
            context += f"- {rel['source']} [{rel['type']}] {rel['target']}"
            if rel.get("description"):
                context += f": {rel['description']}"
            context += "\n"

        if len(relationships) > 15:
            context += f"- ... and {len(relationships) - 15} more relationships\n"

        return context

    def _store_community_summary(self, session, community_id: int, summary: Dict[str, Any]) -> None:
        """
        Store community summary in Neo4j

        Args:
            session: Neo4j session
            community_id: Community ID
            summary: Summary dictionary
        """
        try:
            query = """
            MATCH (c:Community {id: $community_id})
            SET c.summary = $summary,
                c.key_themes = $themes,
                c.summary_timestamp = datetime()
            RETURN c.id
            """

            session.run(
                query,
                {
                    "community_id": community_id,
                    "summary": summary.get("summary", ""),
                    "themes": ",".join(summary.get("themes", [])),
                },
            )

            logger.info(f"Community summary stored for community {community_id}")

        except Exception as e:
            logger.error(f"Failed to store community summary: {str(e)}")

    def summarize_all_communities(self) -> Dict[str, Any]:
        """
        Generate summaries for all communities

        Returns:
            Dictionary with all community summaries
        """
        try:
            session = self.get_session()

            # Get all communities
            query = "MATCH (c:Community) RETURN c.id AS community_id ORDER BY c.id"
            communities = session.run(query).data()

            if not communities:
                return {
                    "status": "no_communities",
                    "message": "No communities found",
                }

            summaries = {}
            for record in communities:
                community_id = record["community_id"]
                result = self.summarize_community(community_id)

                if result["status"] == "success":
                    summaries[community_id] = result

            logger.info(f"Summarized {len(summaries)} communities")
            return {
                "status": "success",
                "num_communities_summarized": len(summaries),
                "summaries": summaries,
            }

        except Exception as e:
            logger.error(f"Failed to summarize all communities: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_community_summary(self, community_id: int) -> Dict[str, Any]:
        """
        Get previously generated community summary

        Args:
            community_id: Community ID

        Returns:
            Dictionary with community summary
        """
        try:
            session = self.get_session()

            query = """
            MATCH (c:Community {id: $community_id})
            RETURN
                c.id AS community_id,
                c.summary AS summary,
                c.key_themes AS key_themes,
                c.summary_timestamp AS summary_timestamp
            """

            result = session.run(query, {"community_id": community_id}).single()

            if result and result["summary"]:
                return {
                    "status": "success",
                    "community_id": result["community_id"],
                    "summary": result["summary"],
                    "key_themes": (result["key_themes"].split(",") if result["key_themes"] else []),
                    "generated_at": result["summary_timestamp"],
                }

            return {"status": "not_found", "community_id": community_id}

        except Exception as e:
            logger.error(f"Failed to get community summary: {str(e)}")
            return {"status": "error", "message": str(e)}

    def compare_communities(self, community_id_1: int, community_id_2: int) -> Dict[str, Any]:
        """
        Compare two communities and find connections

        Args:
            community_id_1: First community ID
            community_id_2: Second community ID

        Returns:
            Dictionary with community comparison
        """
        try:
            session = self.get_session()

            # Find connections between communities
            query = """
            MATCH (c1:Community {id: $community_id_1})<-[r1:IN_COMMUNITY]-(e1:Entity)
            MATCH (c2:Community {id: $community_id_2})<-[r2:IN_COMMUNITY]-(e2:Entity)
            MATCH path = (e1)-[rel]-(e2)
            WHERE type(rel) IN ['RELATED_TO', 'MENTIONED_IN', 'PART_OF']
            RETURN
                collect(DISTINCT e1.name) AS community_1_entities,
                collect(DISTINCT e2.name) AS community_2_entities,
                collect({
                    source: e1.name,
                    target: e2.name,
                    type: type(rel)
                }) AS cross_community_connections,
                count(path) AS connection_count
            """

            result = session.run(
                query,
                {
                    "community_id_1": community_id_1,
                    "community_id_2": community_id_2,
                },
            ).single()

            if result and result["connection_count"] > 0:
                return {
                    "status": "success",
                    "community_1_id": community_id_1,
                    "community_2_id": community_id_2,
                    "community_1_size": len(result["community_1_entities"]),
                    "community_2_size": len(result["community_2_entities"]),
                    "connection_count": result["connection_count"],
                    "connections": result["cross_community_connections"][:10],
                }

            return {
                "status": "not_connected",
                "community_1_id": community_id_1,
                "community_2_id": community_id_2,
                "message": "No direct connections found",
            }

        except Exception as e:
            logger.error(f"Failed to compare communities: {str(e)}")
            return {"status": "error", "message": str(e)}


# Singleton instance
community_summarization_service = CommunitySummarizationService()
