"""
Query service for Q&A system with GraphRAG capabilities
Handles query classification, entity extraction, and answer generation
"""

import logging
from typing import Any, Dict, List, Optional

from app.services.graph_service import graph_service
from app.services.llm_service import llm_service
from app.services.retrieval_service import retrieval_service

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
        include_text: bool = True,
    ) -> Dict[str, Any]:
        """
        Build contextual information from entities following Microsoft GraphRAG methodology
        
        Microsoft GraphRAG requires actual text content from documents, not just entity metadata.
        This method retrieves both entity relationships AND text units for rich context.

        Args:
            entities: Dict of entities
            hop_limit: How many hops to traverse for entity relationships
            include_text: Whether to include text units (strongly recommended per GraphRAG)

        Returns:
            Dict with context string and supporting metadata
        """
        context_parts = []
        text_units_seen = set()  # Avoid duplicate text chunks
        related_entities_total = 0

        for entity_name, entity_data in entities.items():
            # Add entity metadata
            context_parts.append(
                f"**{entity_name}** ({entity_data.get('type', 'UNKNOWN')}) - "
                f"{entity_data.get('description', 'No description')}"
            )

            # Get related entities and text units if entity has an ID
            entity_id = entity_data.get("id")
            if entity_id:
                try:
                    # Retrieve full context including text units (Microsoft GraphRAG pattern)
                    context = self.get_entity_context(entity_id, hop_limit)

                    # Add related entities
                    if context.get("related_entities"):
                        related_entities = context["related_entities"][:5]
                        related_entities_total += len(related_entities)
                        related_info = []
                        for rel_ent in related_entities:
                            rel_type = rel_ent.get("relationship_type", "RELATED_TO")
                            rel_name = rel_ent.get("name", "Unknown")
                            related_info.append(f"{rel_name} ({rel_type})")
                        
                        if related_info:
                            context_parts.append(f"  🔗 Related: {', '.join(related_info)}")
                    
                    # Add text units (CRITICAL for Microsoft GraphRAG)
                    # This provides actual document text to LLM
                    if include_text and context.get("text_units"):
                        text_units = context["text_units"]
                        
                        for text_unit in text_units[:3]:  # Limit to 3 text chunks per entity
                            text_id = text_unit.get("text_unit_id")
                            if text_id and text_id not in text_units_seen:
                                text_content = text_unit.get("text", "")
                                if text_content:
                                    # Truncate very long text
                                    if len(text_content) > 500:
                                        text_content = text_content[:500] + "..."
                                    
                                    context_parts.append(f"  📄 Text excerpt: {text_content}")
                                    text_units_seen.add(text_id)
                        
                        if text_units:
                            logger.debug(f"Added {len(text_units[:3])} text units for entity {entity_name}")
                    
                except Exception as e:
                    logger.warning(f"Could not get context for entity {entity_name}: {e}")

        context_str = "\n".join(context_parts)
        
        # Log context building metrics
        logger.info(f"Built context: {len(entities)} entities, {len(text_units_seen)} unique text units")
        
        return {
            "context": context_str,
            "entity_count": len(entities),
            "related_entities": related_entities_total,
            "text_units_used": len(text_units_seen),
            "context_length": len(context_str),
        }

    def _assemble_global_context(self, retrieval_results: Dict[str, Any]) -> str:
        """
        Assemble global context from communities for LLM (Microsoft GraphRAG methodology)
        
        Args:
            retrieval_results: Results from global retrieval
            
        Returns:
            Formatted context string with community summaries, themes, and significance
        """
        if retrieval_results.get("status") != "success":
            return ""
        
        communities = retrieval_results.get("communities", [])
        
        if not communities:
            return "No communities found in the knowledge graph."
        
        context_parts = [
            f"📊 **Dataset Overview**: {retrieval_results.get('total_entities', 0)} entities "
            f"across {retrieval_results.get('num_communities', 0)} communities\n"
        ]
        
        # Include top communities (up to 10)
        for i, comm in enumerate(communities[:10], 1):
            context_parts.append(f"\n🏘️  **Community {comm['community_id']}** (Level {comm.get('level', 0)}):")
            context_parts.append(f"   • Size: {comm['size']} entities")
            context_parts.append(f"   • Significance: {comm.get('significance', 'medium').upper()}")
            
            # Add summary if available
            if comm.get("summary") and comm["summary"].strip():
                context_parts.append(f"   • Summary: {comm['summary']}")
            
            # Add themes if available
            if comm.get("themes") and comm["themes"].strip():
                themes_list = comm["themes"].split(",")
                themes = ", ".join([t.strip() for t in themes_list if t.strip()])
                if themes:
                    context_parts.append(f"   • Key Themes: {themes}")
        
        # Add note about additional communities if there are more
        if len(communities) > 10:
            context_parts.append(f"\n... and {len(communities) - 10} more communities")
        
        return "\n".join(context_parts)

    def process_global_query(
        self,
        query: str,
    ) -> Dict[str, Any]:
        """
        Process a global/holistic query using community summaries (GraphRAG Global Search)
        
        Args:
            query: User query
            
        Returns:
            Dict with query results including global context
        """
        result = {
            "query": query,
            "status": "error",
            "query_type": "global",
            "context": "",
            "answer": "",
            "num_communities": 0,
            "confidence_score": "0.0",
            "error": None,
            "metadata": {},
            "reasoning_steps": [],
        }
        reasoning_steps: List[Dict[str, str]] = []
        metadata: Dict[str, Any] = {}
        
        try:
            logger.info(f"Processing global query: {query}")
            
            # Step 1: Retrieve global context with community summaries
            retrieval_results = retrieval_service.retrieve_global_context(use_summaries=True)
            
            if retrieval_results.get("status") != "success":
                result["error"] = retrieval_results.get("message", "Failed to retrieve global context")
                logger.error(f"Global retrieval failed: {result['error']}")
                reasoning_steps.append(
                    {"step": "global_retrieval", "detail": result["error"]}
                )
                result["reasoning_steps"] = reasoning_steps
                result["metadata"] = metadata
                return result
            
            result["num_communities"] = retrieval_results.get("num_communities", 0)
            metadata["num_communities"] = result["num_communities"]
            metadata["total_entities"] = retrieval_results.get("total_entities")
            reasoning_steps.append(
                {
                    "step": "global_retrieval",
                    "detail": f"Retrieved {result['num_communities']} communities with summaries",
                }
            )
            
            # Check if summaries are available
            if not retrieval_results.get("summaries_available", False):
                logger.warning("No community summaries available for global search")
                result["error"] = "Community summaries not yet generated. Please process documents first."
                reasoning_steps.append(
                    {
                        "step": "global_retrieval",
                        "detail": result["error"],
                    }
                )
                result["reasoning_steps"] = reasoning_steps
                result["metadata"] = metadata
                return result
            
            # Step 2: Assemble context from community summaries
            context = self._assemble_global_context(retrieval_results)
            result["context"] = context
            metadata["context_length"] = len(context)
            
            # Step 3: Generate answer using LLM with global context
            answer_result = llm_service.generate_answer(
                query=query,
                context=context,
                citations=[
                    f"Community {c['community_id']} ({c['size']} entities)"
                    for c in retrieval_results.get("communities", [])[:5]
                ],
            )
            
            result["answer"] = answer_result.get("answer", "")
            result["citations"] = answer_result.get("citations", [])
            result["confidence_score"] = answer_result.get("confidence_score", "0.0")
            result["status"] = "success"
            metadata["answer_length"] = len(result["answer"])
            reasoning_steps.append(
                {
                    "step": "generate_answer",
                    "detail": f"Generated global answer with confidence {result['confidence_score']}",
                }
            )
            
            logger.info(f"Global query processed successfully with {result['num_communities']} communities")
            
        except Exception as e:
            logger.error(f"Global query processing error: {e}", exc_info=True)
            result["error"] = str(e)
            reasoning_steps.append({"step": "error", "detail": str(e)})
        
        result["reasoning_steps"] = reasoning_steps
        result["metadata"] = metadata
        
        return result

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
            "metadata": {},
            "reasoning_steps": [],
            "context": "",
            "answer": "",
            "citations": [],
            "confidence_score": "0.0",
            "error": None,
        }
        reasoning_steps: List[Dict[str, str]] = []
        metadata: Dict[str, Any] = {
            "hop_limit": hop_limit,
            "document_id": document_id,
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
                reasoning_steps.append(
                    {
                        "step": "classify_query",
                        "detail": result["error"],
                    }
                )
                result["reasoning_steps"] = reasoning_steps
                result["metadata"] = metadata
                return result

            query_type = classification["classification"].get("type", "EXPLORATORY")
            key_entities = classification["classification"].get("key_entities", [])
            result["query_type"] = query_type
            metadata["query_type"] = query_type
            metadata["classified_entities"] = key_entities
            reasoning_steps.append(
                {
                    "step": "classify_query",
                    "detail": f"Detected '{query_type}' query with {len(key_entities)} key entities",
                }
            )

            logger.info(f"Query type: {query_type}, Key entities: {key_entities}")

            # Step 2: Find entities in graph
            if not key_entities:
                # If LLM didn't extract entities, use fallback
                key_entities = self.extract_query_entities(query)
                metadata["fallback_entity_extraction"] = True
                reasoning_steps.append(
                    {
                        "step": "entity_extraction_fallback",
                        "detail": f"Fallback extractor found {len(key_entities)} candidate entities",
                    }
                )

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
                    reasoning_steps.append(
                        {
                            "step": "entity_lookup",
                            "detail": result["error"],
                        }
                    )
                    result["reasoning_steps"] = reasoning_steps
                    result["metadata"] = metadata
                    return result

            result["entities_found"] = list(found_entities.keys())
            metadata["entities_found_count"] = len(found_entities)
            reasoning_steps.append(
                {
                    "step": "entity_lookup",
                    "detail": f"Resolved {len(found_entities)} entities in the graph",
                }
            )

            # Step 3: Build context from entities
            context_result = self.build_context_from_entities(found_entities, hop_limit)
            context = context_result.get("context", "")
            result["context"] = context
            metadata.update(
                {
                    "context_length": context_result.get("context_length", 0),
                    "text_units_used": context_result.get("text_units_used", 0),
                    "related_entities": context_result.get("related_entities", 0),
                }
            )
            reasoning_steps.append(
                {
                    "step": "build_context",
                    "detail": (
                        f"Compiled context with {context_result.get('text_units_used', 0)} text units "
                        f"and {context_result.get('related_entities', 0)} related entities"
                    ),
                }
            )

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
            metadata["answer_length"] = len(result["answer"])
            reasoning_steps.append(
                {
                    "step": "generate_answer",
                    "detail": f"Generated answer with confidence {result['confidence_score']}",
                }
            )

            logger.info(f"Query processed successfully, found {len(found_entities)} entities")

        except Exception as e:
            logger.error(f"Query processing error: {e}", exc_info=True)
            result["error"] = str(e)
            reasoning_steps.append(
                {
                    "step": "error",
                    "detail": str(e),
                }
            )

        result["reasoning_steps"] = reasoning_steps
        result["metadata"] = metadata

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
