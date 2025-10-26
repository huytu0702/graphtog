"""
LLM service for document processing and entity extraction
Uses Google Gemini 2.5 Flash for efficient processing
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import google.generativeai as genai
from google.api_core import retry

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)


class LLMService:
    """Service for LLM-based document processing and extraction"""

    def __init__(self):
        """Initialize LLM service"""
        self.model_name = "gemini-2.5-flash"
        self.rate_limit_delay = 1.0 / 60  # 60 requests per minute
        self.last_request_time = 0
        self.max_retries = 3
        self.retry_delay = 1

    def _apply_rate_limit(self):
        """Apply rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _retry_with_backoff(self, func, *args, **kwargs):
        """Retry logic with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise
                wait_time = self.retry_delay * (2**attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)

    @staticmethod
    def _parse_json_response(response: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM
        Handles markdown code blocks and invalid JSON
        """
        # Try direct parse first
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try removing markdown code blocks
        if response.startswith("```"):
            lines = response.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_block = not in_block
                elif in_block:
                    json_lines.append(line)
            if json_lines:
                try:
                    return json.loads("\n".join(json_lines))
                except json.JSONDecodeError:
                    pass

        logger.error(f"Failed to parse response as JSON: {response[:200]}")
        return {}

    def extract_entities(self, text: str, chunk_id: str) -> Dict[str, Any]:
        """
        Extract entities from text using Gemini

        Args:
            text: Text to extract entities from
            chunk_id: Identifier for the text chunk

        Returns:
            Dict with extracted entities
        """
        prompt = f"""Extract entities from the following text. For each entity, provide:
- name: The entity name
- type: One of PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT, PRODUCT, OTHER
- description: 1-2 sentence description
- confidence: 0.0-1.0 confidence score

Return as JSON array:
[{{"name": "...", "type": "...", "description": "...", "confidence": ...}}, ...]

TEXT:
{text}

JSON:"""

        self._apply_rate_limit()

        def call_llm():
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text

        response_text = self._retry_with_backoff(call_llm)

        try:
            entities = self._parse_json_response(response_text)
            if isinstance(entities, dict):
                entities = entities.get("entities", [])
            return {
                "chunk_id": chunk_id,
                "entities": entities,
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Entity extraction error: {e}")
            return {
                "chunk_id": chunk_id,
                "entities": [],
                "status": "error",
                "error": str(e),
            }

    def extract_relationships(
        self, text: str, entities: List[Dict], chunk_id: str
    ) -> Dict[str, Any]:
        """
        Extract relationships between entities

        Args:
            text: Original text
            entities: Extracted entities
            chunk_id: Identifier for the text chunk

        Returns:
            Dict with extracted relationships
        """
        entity_names = [e["name"] for e in entities]

        prompt = f"""Extract relationships between entities in the text.
Relationships should be between entities from this list: {entity_names}

For each relationship, provide:
- source: Source entity name
- target: Target entity name
- type: One of RELATED_TO, MENTIONS, CAUSES, PRECEDES, OPPOSES, SUPPORTS, CONTAINS, PART_OF
- description: 1-2 sentence description
- confidence: 0.0-1.0 confidence score

Return as JSON array:
[{{"source": "...", "target": "...", "type": "...", "description": "...", "confidence": ...}}, ...]

TEXT:
{text}

JSON:"""

        self._apply_rate_limit()

        def call_llm():
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text

        response_text = self._retry_with_backoff(call_llm)

        try:
            relationships = self._parse_json_response(response_text)
            if isinstance(relationships, dict):
                relationships = relationships.get("relationships", [])
            return {
                "chunk_id": chunk_id,
                "relationships": relationships,
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Relationship extraction error: {e}")
            return {
                "chunk_id": chunk_id,
                "relationships": [],
                "status": "error",
                "error": str(e),
            }

    async def batch_extract_entities(self, chunks: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        """
        Batch extract entities from multiple chunks

        Args:
            chunks: List of (text, chunk_id) tuples

        Returns:
            List of extraction results
        """
        results = []
        for text, chunk_id in chunks:
            result = self.extract_entities(text, chunk_id)
            results.append(result)
            # Small delay between requests for rate limiting
            await asyncio.sleep(0.1)
        return results

    async def batch_extract_relationships(
        self, chunks_with_entities: List[Tuple[str, List[Dict], str]]
    ) -> List[Dict[str, Any]]:
        """
        Batch extract relationships from multiple chunks

        Args:
            chunks_with_entities: List of (text, entities, chunk_id) tuples

        Returns:
            List of extraction results
        """
        results = []
        for text, entities, chunk_id in chunks_with_entities:
            if entities:  # Only extract if there are entities
                result = self.extract_relationships(text, entities, chunk_id)
                results.append(result)
            await asyncio.sleep(0.1)
        return results

    def classify_query(self, query: str) -> Dict[str, Any]:
        """
        Classify query type for intelligent retrieval routing

        Args:
            query: User query

        Returns:
            Dict with query classification
        """
        prompt = f"""Classify this query type. Return JSON with:
- type: One of FACTUAL, ANALYTICAL, EXPLORATORY, COMPARISON
- reasoning: Brief explanation
- key_entities: List of likely key entities to search for
- suggested_depth: Number from 1-3 (1=local/simple, 2=community, 3=global/complex)

QUERY: {query}

JSON:"""

        self._apply_rate_limit()

        def call_llm():
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text

        response_text = self._retry_with_backoff(call_llm)

        try:
            classification = self._parse_json_response(response_text)
            return {
                "query": query,
                "classification": classification,
                "status": "success",
            }
        except Exception as e:
            logger.error(f"Query classification error: {e}")
            return {
                "query": query,
                "classification": {"type": "EXPLORATORY", "depth": 2},
                "status": "error",
            }

    def generate_answer(
        self,
        query: str,
        context: str,
        citations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate answer based on query and retrieved context

        Args:
            query: User query
            context: Retrieved context from graph
            citations: List of source citations

        Returns:
            Dict with generated answer
        """
        citations_text = (
            f"\n\nCitations:\n" + "\n".join([f"- {c}" for c in citations]) if citations else ""
        )

        prompt = f"""Answer the following question based on the provided context.
Be concise and accurate. If the context doesn't contain enough information, say so.

QUESTION: {query}

CONTEXT:
{context}{citations_text}

ANSWER:"""

        self._apply_rate_limit()

        def call_llm():
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text

        response_text = self._retry_with_backoff(call_llm)

        return {
            "query": query,
            "answer": response_text.strip(),
            "citations": citations or [],
            "status": "success",
        }

    def summarize_community(
        self,
        entity_names: List[str],
        relationships_desc: str,
        sample_text: str,
    ) -> Dict[str, Any]:
        """
        Generate summary for a community of entities

        Args:
            entity_names: List of entity names in community
            relationships_desc: Description of relationships
            sample_text: Sample text chunks related to community

        Returns:
            Dict with community summary
        """
        prompt = f"""Create a concise summary (2-3 sentences) of this community of related entities.

ENTITIES: {", ".join(entity_names)}

RELATIONSHIPS:
{relationships_desc}

SAMPLE TEXT:
{sample_text}

SUMMARY:"""

        self._apply_rate_limit()

        def call_llm():
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text

        response_text = self._retry_with_backoff(call_llm)

        return {
            "summary": response_text.strip(),
            "status": "success",
        }

    def generate_community_summary(self, context: str) -> Dict[str, Any]:
        """
        Generate summary for a community

        Args:
            context: Community context with entities and relationships

        Returns:
            Dictionary with summary and themes
        """
        try:
            self._apply_rate_limit()

            prompt = f"""Based on the following community of entities and their relationships, generate a concise summary:

{context}

Provide:
1. A brief summary (2-3 sentences) of what this community represents
2. Key themes (list 3-5 main themes)
3. Main focus area (one line)

Format your response as JSON:
{{
    "summary": "...",
    "themes": ["theme1", "theme2", "..."],
    "focus_area": "..."
}}
"""

            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)

            # Extract JSON from response
            try:
                result_text = response.text.strip()
                # Remove markdown code blocks if present
                if result_text.startswith("```json"):
                    result_text = result_text[7:]
                if result_text.endswith("```"):
                    result_text = result_text[:-3]

                result = json.loads(result_text)
                logger.info("Community summary generated successfully")
                return result
            except json.JSONDecodeError:
                logger.warning("Could not parse community summary JSON")
                return {
                    "summary": response.text[:200],
                    "themes": [],
                    "focus_area": "Unknown",
                }

        except Exception as e:
            logger.error(f"Community summary generation failed: {str(e)}")
            return {
                "summary": "Summary generation failed",
                "themes": [],
                "focus_area": "Error",
            }


# Export singleton instance
llm_service = LLMService()
