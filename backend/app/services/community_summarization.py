"""
Community summarization service for GraphRAG
Generates natural language summaries of communities following Microsoft GraphRAG methodology
"""

import json
import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from app.config import get_settings
from app.db.neo4j import get_neo4j_session

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure Gemini
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)


class CommunitySummarizationService:
    """Service for generating community summaries following Microsoft GraphRAG"""

    def __init__(self):
        """Initialize community summarization service"""
        self.session = None
        self.model_name = "gemini-2.5-flash-lite"

    def get_session(self):
        """Get or create Neo4j session"""
        if not self.session:
            self.session = get_neo4j_session()
        return self.session

    def get_community_context(
        self, community_id: int, max_members: int = 20
    ) -> Dict[str, Any]:
        """
        Retrieve context for a community

        Args:
            community_id: Community ID
            max_members: Max members to include

        Returns:
            Dictionary with community context
        """
        try:
            session = self.get_session()

            # Get community members and their relationships
            query = """
            MATCH (c:Community {id: $community_id})<-[r:IN_COMMUNITY]-(e:Entity)
            WITH c, e, r
            OPTIONAL MATCH (e)-[rel]-(other:Entity)-[:IN_COMMUNITY]->(c)
            WITH c, e, collect(DISTINCT {
                source: e.name,
                target: other.name,
                type: type(rel),
                description: rel.description
            }) AS entity_rels
            RETURN
                c.id AS community_id,
                c.level AS community_level,
                collect(DISTINCT {
                    name: e.name,
                    type: e.type,
                    description: e.description,
                    mention_count: e.mention_count,
                    confidence: e.confidence
                })[0..$max_members] AS members,
                entity_rels[0..30] AS relationships,
                count(DISTINCT e) AS member_count
            """

            result = session.run(query, {
                "community_id": community_id,
                "max_members": max_members
            }).single()

            if result:
                return {
                    "status": "success",
                    "community_id": result["community_id"],
                    "community_level": result.get("community_level", 0),
                    "members": result["members"],
                    "relationships": result["relationships"],
                    "member_count": result["member_count"]
                }

            return {"status": "not_found", "community_id": community_id}

        except Exception as e:
            logger.error(f"Failed to get community context: {str(e)}")
            return {"status": "error", "message": str(e)}

    def generate_community_summary(
        self, community_id: int, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a summary for a community following Microsoft GraphRAG methodology

        Args:
            community_id: Community ID
            context: Optional pre-fetched context

        Returns:
            Dictionary with summary
        """
        try:
            # Get context if not provided
            if not context:
                context = self.get_community_context(community_id)

            if context.get("status") != "success":
                return {
                    "status": "error",
                    "message": f"Could not get context for community {community_id}"
                }

            # Prepare summary prompt
            members_text = "\n".join([
                f"- {m['name']} ({m['type']}): {m.get('description', 'N/A')}"
                for m in context.get("members", [])[:10]
            ])

            relationships_text = "\n".join([
                f"- {r['source']} --{r['type']}--> {r['target']}: {r.get('description', '')}"
                for r in context.get("relationships", [])[:10]
                if r.get('source') and r.get('target')
            ])

            prompt = f"""Generate a comprehensive summary of this community in 2-3 sentences:

Community Level: {context.get('community_level', 0)}
Member Count: {context.get('member_count', 0)}

Key Members:
{members_text}

Key Relationships:
{relationships_text}

Provide:
1. A brief summary of what this community represents
2. Main themes or topics (3-5 themes)
3. Significance/importance (high/medium/low)

Format as JSON:
{{
    "summary": "...",
    "themes": ["...", "..."],
    "significance": "high|medium|low"
}}
"""

            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)

            try:
                result_text = response.text.strip()
                if result_text.startswith("```"):
                    result_text = result_text.split("```")[1]
                    if result_text.startswith("json"):
                        result_text = result_text[4:]
                    result_text = result_text.strip()

                summary_data = json.loads(result_text)
                return {
                    "status": "success",
                    "community_id": community_id,
                    "summary": summary_data.get("summary", ""),
                    "themes": summary_data.get("themes", []),
                    "significance": summary_data.get("significance", "medium"),
                }
            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse summary JSON: {e}")
                # Fallback to raw text
                return {
                    "status": "success",
                    "community_id": community_id,
                    "summary": response.text.strip()[:200],
                    "themes": [],
                    "significance": "medium",
                }

        except Exception as e:
            logger.error(f"Failed to generate community summary: {str(e)}")
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
            failed = 0
            for record in communities:
                community_id = record["community_id"]
                
                # Get context and generate summary
                context = self.get_community_context(community_id)
                if context.get("status") == "success":
                    result = self.generate_community_summary(community_id, context)
                    
                    if result["status"] == "success":
                        # Store summary in Neo4j
                        self._store_community_summary(
                            session,
                            community_id,
                            result
                        )
                        summaries[community_id] = result
                    else:
                        failed += 1
                        logger.warning(f"Failed to generate summary for community {community_id}")
                else:
                    failed += 1
                    logger.warning(f"Failed to get context for community {community_id}")

            logger.info(f"Summarized {len(summaries)} communities ({failed} failed)")
            return {
                "status": "success",
                "num_communities_summarized": len(summaries),
                "failed": failed,
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
