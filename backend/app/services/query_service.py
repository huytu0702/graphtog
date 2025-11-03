"""
Enhanced Query Service with ToG integration and automatic query type classification.

Supports routing queries to appropriate processing methods:
- local: Entity-specific queries
- global: Dataset-wide holistic queries
- hybrid: Mixed local and global aspects
- tog: Multi-hop reasoning queries (Tree of Graphs)
"""

import logging
from typing import Dict, List, Optional, Tuple, Any

from app.services.llm_service import LLMService
from app.services.graph_service import GraphService

logger = logging.getLogger(__name__)


class QueryService:
    """Enhanced query service with automatic query type classification and ToG support."""

    def __init__(self):
        """Initialize the query service."""
        self.llm_service = LLMService()
        self.graph_service = GraphService()

    async def process_query(
        self,
        question: str,
        document_ids: Optional[List[int]] = None,
        query_type: Optional[str] = None,
        tog_config: Optional[Any] = None
    ) -> Tuple[str, str, float, Dict[str, Any]]:
        """
        Process query with automatic or manual query type selection.

        Returns:
            Tuple of (answer, query_type_used, confidence, metadata)
        """
        # Auto-classify if not specified
        if query_type is None:
            query_type = await self._classify_query_type(question)

        # Route to appropriate method
        if query_type == "tog":
            return await self._process_tog_query(question, document_ids, tog_config)
        elif query_type == "local":
            return await self._process_local_query(question, document_ids)
        elif query_type == "global":
            return await self._process_global_query(question, document_ids)
        elif query_type == "hybrid":
            return await self._process_hybrid_query(question, document_ids)
        else:
            raise ValueError(f"Unknown query type: {query_type}")

    async def _classify_query_type(self, question: str) -> str:
        """
        Classify question into query type using LLM.

        Classification logic:
        - Multi-hop questions (how is X connected to Y) → tog
        - Specific entity questions → local
        - Broad thematic questions → global
        - Mixed questions → hybrid
        """
        prompt = f"""Classify the following question into one of these query types:

1. **local**: Questions about specific entities or relationships
   - Example: "What is the relationship between X and Y?"
   - Example: "Tell me about entity X"

2. **global**: Broad questions about themes, trends, or summaries
   - Example: "What are the main themes in the documents?"
   - Example: "Summarize the key findings"

3. **hybrid**: Questions that combine specific and broad aspects
   - Example: "How does X relate to the overall theme?"
   - Example: "What is the connection between entity A and the main topic?"

4. **tog**: Questions requiring multi-hop reasoning or connection discovery
   - Example: "How is X connected to Y through intermediate entities?"
   - Example: "What is the chain of relationships between A and B?"
   - Example: "Trace the path from X to Y"
   - Example: "How does A influence B indirectly?"

Question: {question}

Return JSON: {{"query_type": "local|global|hybrid|tog", "reasoning": "brief explanation"}}

Return only the JSON object, no other text.
"""

        try:
            response = await self.llm_service.generate_text(prompt, temperature=0.0)
            result = self.llm_service._parse_json_response(response)

            query_type = result.get("query_type", "hybrid")
            reasoning = result.get("reasoning", "")

            logger.info(f"Classified query '{question[:50]}...' as {query_type}: {reasoning}")
            return query_type

        except Exception as e:
            logger.warning(f"Query classification failed: {e}, defaulting to hybrid")
            return "hybrid"

    async def _process_tog_query(
        self,
        question: str,
        document_ids: Optional[List[int]],
        config: Optional[Any]
    ) -> Tuple[str, str, float, Dict[str, Any]]:
        """Process query using ToG reasoning."""
        from app.services.tog_service import ToGService, ToGConfig

        config = config or ToGConfig()

        tog_service = ToGService(self.graph_service, self.llm_service)
        reasoning_path = await tog_service.process_query(question, config)

        answer = reasoning_path.final_answer or "No answer generated"
        confidence = reasoning_path.confidence_score

        metadata = {
            "reasoning_path": reasoning_path.steps,
            "retrieved_triplets": reasoning_path.retrieved_triplets,
            "config": config.__dict__ if hasattr(config, '__dict__') else config,
            "sufficiency_status": reasoning_path.sufficiency_status
        }

        return answer, "tog", confidence, metadata

    async def _process_local_query(
        self, question: str, document_ids: Optional[List[int]]
    ) -> Tuple[str, str, float, Dict[str, Any]]:
        """Process local entity-specific query."""
        # For now, return a placeholder - this would integrate with existing local query logic
        # TODO: Integrate with existing local query processing

        answer = f"This is a local query about: '{question}'. Local query processing not yet fully integrated."
        confidence = 0.7

        metadata = {
            "query_type": "local",
            "document_ids": document_ids
        }

        return answer, "local", confidence, metadata

    async def _process_global_query(
        self, question: str, document_ids: Optional[List[int]]
    ) -> Tuple[str, str, float, Dict[str, Any]]:
        """Process global dataset-wide query."""
        # For now, return a placeholder - this would integrate with existing global query logic
        # TODO: Integrate with existing global query processing

        answer = f"This is a global query about: '{question}'. Global query processing not yet fully integrated."
        confidence = 0.8

        metadata = {
            "query_type": "global",
            "document_ids": document_ids
        }

        return answer, "global", confidence, metadata

    async def _process_hybrid_query(
        self, question: str, document_ids: Optional[List[int]]
    ) -> Tuple[str, str, float, Dict[str, Any]]:
        """Process hybrid query combining local and global aspects."""
        # For now, return a placeholder - this would combine local and global processing
        # TODO: Implement hybrid query processing

        answer = f"This is a hybrid query about: '{question}'. Hybrid query processing not yet implemented."
        confidence = 0.6

        metadata = {
            "query_type": "hybrid",
            "document_ids": document_ids
        }

        return answer, "hybrid", confidence, metadata

    # Placeholder methods for existing functionality (to be integrated)
    def process_global_query(self, question: str) -> Dict[str, Any]:
        """Placeholder for existing global query processing."""
        return {
            "answer": f"Global query result for: {question}",
            "query_type": "global",
            "confidence_score": 0.8,
            "context": f"Processed global query: {question}"
        }

    def process_query(self, question: str, hop_limit: int = 1, document_id: Optional[int] = None) -> Dict[str, Any]:
        """Placeholder for existing local query processing."""
        return {
            "answer": f"Local query result for: {question}",
            "query_type": "local",
            "confidence_score": 0.7,
            "context": f"Processed local query: {question}"
        }

    def batch_process_queries(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Placeholder for batch processing."""
        return [
            {"answer": f"Batch result {i+1}", "query_type": "batch", "confidence_score": 0.5}
            for i, _ in enumerate(queries)
        ]

    def get_all_claims(self, **kwargs) -> Dict[str, Any]:
        """Placeholder for claims retrieval."""
        return {"status": "success", "claims": [], "total": 0}

    def get_claims_for_entity(self, **kwargs) -> Dict[str, Any]:
        """Placeholder for entity claims retrieval."""
        return {"status": "success", "claims": [], "total": 0}

    def query_claims(self, **kwargs) -> Dict[str, Any]:
        """Placeholder for claims querying."""
        return {"status": "success", "answer": "Claims query result", "claims": []}


# Global instance for backward compatibility
query_service = QueryService()
