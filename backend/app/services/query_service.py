"""
Query service for Q&A system with GraphRAG capabilities
Handles query classification, entity extraction, and answer generation
"""

import logging
from typing import Any, Dict, List, Optional

from app.services.graph_service import graph_service
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class QueryService:
    """Service for processing queries and generating answers"""

    def __init__(self):
        """Initialize query service"""
        pass

    def extract_query_entities(self, query: str) -> List[str]:
        """
        Extract key entities from a query

        Args:
            query: User query

        Returns:
            List of entity names to search for
        """
        # Use LLM to classify and extract key entities
        classification = llm_service.classify_query(query)

        if classification["status"] == "success":
            return classification["classification"].get("key_entities", [])

        # Fallback: simple keyword extraction
        # Extract capitalized words as potential entity names
        import re

        words = re.findall(r"\b[A-Z][a-z]+\b", query)
        return words or []

    def find_entities_in_graph(self, entity_names: List[str]) -> Dict[str, Any]:
        """
        Find entities in the graph that match query

        Args:
            entity_names: List of entity names to search for

        Returns:
            Dict with found entities and their data
        """
        found_entities = {}

        for entity_name in entity_names:
            entity = graph_service.find_entity_by_name(entity_name)
            if entity:
                found_entities[entity_name] = entity

        return found_entities

    def get_entity_context(
        self,
        entity_id: str,
        hop_limit: int = 2,
    ) -> Dict[str, Any]:
        """
        Get context around an entity

        Args:
            entity_id: Entity to get context for
            hop_limit: How many hops to traverse

        Returns:
            Context dict with related entities and relationships
        """
        return graph_service.get_entity_context(entity_id, hop_limit)

    def build_context_from_entities(
        self,
        entities: Dict[str, Any],
        hop_limit: int = 1,
    ) -> str:
        """
        Build contextual information from entities

        Args:
            entities: Dict of entities
            hop_limit: How many hops to traverse

        Returns:
            Formatted context string
        """
        context_parts = []

        for entity_name, entity_data in entities.items():
            context_parts.append(
                f"**{entity_name}** ({entity_data.get('type', 'UNKNOWN')}) - "
                f"{entity_data.get('description', 'No description')}"
            )

            # Get related entities if entity has an ID
            entity_id = entity_data.get("id")
            if entity_id:
                try:
                    context = self.get_entity_context(entity_id, hop_limit)

                    if context.get("related_entities"):
                        related_str = ", ".join(
                            [e["name"] for e in context["related_entities"][:5]]
                        )
                        context_parts.append(f"  Related to: {related_str}")
                except Exception as e:
                    logger.warning(f"Could not get context for entity {entity_name}: {e}")

        return "\n".join(context_parts)

    def process_query(
        self,
        query: str,
        hop_limit: int = 1,
        document_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a query end-to-end

        Args:
            query: User query
            hop_limit: Graph traversal depth
            document_id: Optional document ID to filter entities

        Returns:
            Dict with query results
        """
        result = {
            "query": query,
            "status": "error",
            "query_type": "unknown",
            "entities_found": [],
            "context": "",
            "answer": "",
            "citations": [],
            "confidence_score": "0.0",
            "error": None,
        }

        try:
            # Step 1: Classify query
            logger.info(f"Processing query: {query}")
            classification = llm_service.classify_query(query)

            if classification["status"] != "success":
                result["error"] = "Failed to classify query: " + classification.get(
                    "error", "Unknown error"
                )
                logger.error(f"Query classification failed: {result['error']}")
                return result

            query_type = classification["classification"].get("type", "EXPLORATORY")
            key_entities = classification["classification"].get("key_entities", [])
            result["query_type"] = query_type

            logger.info(f"Query type: {query_type}, Key entities: {key_entities}")

            # Step 2: Find entities in graph
            if not key_entities:
                # If LLM didn't extract entities, use fallback
                key_entities = self.extract_query_entities(query)

            found_entities = self.find_entities_in_graph(key_entities)

            # Fallback: If no specific entities found, get top entities from graph
            if not found_entities:
                logger.info(f"No specific entities found, retrieving top entities from graph")
                # Filter by document_id if provided
                top_entities_list = graph_service.get_top_entities(
                    limit=10, document_id=document_id
                )

                if top_entities_list:
                    # Convert list to dict format expected by rest of the code
                    found_entities = {entity["name"]: entity for entity in top_entities_list}
                    logger.info(
                        f"Retrieved {len(found_entities)} top entities as fallback"
                        + (f" from document {document_id}" if document_id else "")
                    )
                    logger.debug(
                        f"Sample entity structure: {list(found_entities.values())[0] if found_entities else 'None'}"
                    )
                else:
                    result["status"] = "no_entities_found"
                    result["error"] = "No entities found in knowledge graph" + (
                        f" for document {document_id}" if document_id else ""
                    )
                    logger.info(
                        f"No entities found in graph"
                        + (f" for document {document_id}" if document_id else "")
                    )
                    return result

            result["entities_found"] = list(found_entities.keys())

            # Step 3: Build context from entities
            context = self.build_context_from_entities(found_entities, hop_limit)
            result["context"] = context

            # Step 4: Generate answer
            answer_result = llm_service.generate_answer(
                query=query,
                context=context,
                citations=[f"{name} ({data['type']})" for name, data in found_entities.items()],
            )

            result["answer"] = answer_result.get("answer", "")
            result["citations"] = answer_result.get("citations", [])
            result["confidence_score"] = answer_result.get("confidence_score", "0.0")
            result["status"] = "success"

            logger.info(f"Query processed successfully, found {len(found_entities)} entities")

        except Exception as e:
            logger.error(f"Query processing error: {e}", exc_info=True)
            result["error"] = str(e)

        return result

    def batch_process_queries(
        self,
        queries: List[str],
        hop_limit: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Process multiple queries

        Args:
            queries: List of queries
            hop_limit: Graph traversal depth

        Returns:
            List of results
        """
        results = []
        for query in queries:
            result = self.process_query(query, hop_limit)
            results.append(result)

        return results


# Export singleton instance
query_service = QueryService()
