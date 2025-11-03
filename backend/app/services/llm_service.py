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
from app.services.prompt import (
    DEFAULT_COMPLETION_DELIMITER,
    DEFAULT_RECORD_DELIMITER,
    DEFAULT_TUPLE_DELIMITER,
    build_claims_extraction_prompt,
    build_community_summary_prompt,
    build_contextual_answer_prompt,
    build_entity_extraction_prompt,
    build_graph_community_summary_prompt,
    build_map_reduce_batch_summary_prompt,
    build_map_reduce_final_synthesis_prompt,
    build_query_classification_prompt,
    build_relationship_extraction_prompt,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# Configure Gemini only if API key is provided
if settings.GOOGLE_API_KEY:
    genai.configure(api_key=settings.GOOGLE_API_KEY)
else:
    logger.warning("GOOGLE_API_KEY not configured. Please set GOOGLE_API_KEY environment variable.")


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
                error_msg = str(e)
                # Check if it's an API key error
                if "API_KEY" in error_msg or "No API_KEY" in error_msg:
                    logger.error(
                        f"API key not configured. Please set GOOGLE_API_KEY environment variable. "
                        f"Get your key from https://ai.google.dev/"
                    )
                    raise
                if attempt == self.max_retries - 1:
                    raise
                wait_time = self.retry_delay * (2**attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)

    @staticmethod
    def _parse_json_response(response: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM
        Handles markdown code blocks, control characters, and invalid JSON
        """
        import re

        # Check for empty or None response
        if not response:
            logger.warning("Empty response received from LLM")
            return {}

        # Clean the response first
        cleaned_response = response.strip()

        # Check again after stripping
        if not cleaned_response:
            logger.warning("Response is empty after stripping whitespace")
            return {}

        # Try direct parse first
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            pass

        # Try removing markdown code blocks
        if cleaned_response.startswith("```"):
            lines = cleaned_response.split("\n")
            json_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_block = not in_block
                elif in_block:
                    json_lines.append(line)
            if json_lines:
                try:
                    cleaned_response = "\n".join(json_lines).strip()
                except Exception:
                    pass

        # Check if still empty after code block removal
        if not cleaned_response:
            logger.warning("Response is empty after removing code blocks")
            return {}

        # Remove invalid control characters (keep newlines, tabs, carriage returns)
        # JSON spec allows: \t \n \r and escaped control chars like \u0000
        # Remove other control chars (0x00-0x1F except \t\n\r)
        cleaned_response = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", cleaned_response)

        # Final check
        if not cleaned_response:
            logger.warning("Response is empty after control character removal")
            return {}

        # Try parsing the cleaned response
        try:
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response as JSON after cleaning: {str(e)[:100]}")
            logger.debug(f"Response preview (first 500 chars): {cleaned_response[:500]}")
            logger.debug(f"Response length after cleaning: {len(cleaned_response)} characters")
            # Also log the raw response for debugging
            if response:
                logger.debug(f"Original response preview (first 200 chars): {response[:200]}")

        return {}

    @staticmethod
    def _parse_graph_extraction_response(
        response: str,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parse GraphRAG tuple-based extraction output into structured entities and relationships.

        Returns:
            Tuple of (entities, relationships)
        """
        if not response:
            return [], []

        # Strip code fences if present
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            content_lines = []
            in_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    content_lines.append(line)
            text = "\n".join(content_lines).strip() if content_lines else text

        if not text:
            return [], []

        text = text.replace("\r\n", "\n")
        text = text.replace(DEFAULT_COMPLETION_DELIMITER, " ").strip()

        records: List[str] = []
        buffer: List[str] = []
        for line in text.split(DEFAULT_RECORD_DELIMITER):
            stripped = line.strip()
            if not stripped:
                continue
            if stripped == DEFAULT_COMPLETION_DELIMITER.strip():
                break

            if stripped.startswith("("):
                if buffer:
                    record = " ".join(buffer).strip()
                    if record.startswith("(") and record.endswith(")"):
                        records.append(record)
                buffer = [stripped]
            elif buffer:
                buffer.append(stripped)
            else:
                continue

            if stripped.endswith(")") and buffer:
                record = " ".join(buffer).strip()
                if record.startswith("(") and record.endswith(")"):
                    records.append(record)
                buffer = []

        if buffer:
            record = " ".join(buffer).strip()
            if record.startswith("(") and record.endswith(")"):
                records.append(record)

        entities: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []

        for record in records:
            normalized = record
            if normalized.startswith("(") and normalized.endswith(")"):
                normalized = normalized[1:-1]
            parts = [
                part.strip().strip('"').strip("'")
                for part in normalized.split(DEFAULT_TUPLE_DELIMITER)
            ]
            if len(parts) < 4:
                continue

            record_type = parts[0].lower()
            if record_type == "entity":
                entity_name = parts[1]
                entity_type = parts[2]
                description = parts[3]
                entity = {
                    "name": entity_name,
                    "type": entity_type.upper(),
                    "description": description,
                    "context": description,
                    "confidence": 0.8,
                }
                entities.append(entity)
            elif record_type == "relationship" and len(parts) >= 5:
                source_entity = parts[1]
                target_entity = parts[2]
                relationship_description = parts[3]
                strength_raw = parts[4]
                try:
                    strength_value = float(strength_raw)
                except ValueError:
                    strength_value = 5.0

                relationship = {
                    "source": source_entity,
                    "target": target_entity,
                    "description": relationship_description,
                    "type": "RELATED_TO",
                    "confidence": max(0.0, min(strength_value / 10.0, 1.0)),
                    "strength": strength_value,
                }
                relationships.append(relationship)

        return entities, relationships

    def extract_entities(self, text: str, chunk_id: str) -> Dict[str, Any]:
        """
        Extract entities from text using Gemini
        Args:
            text: Text to extract entities from
            chunk_id: Identifier for the text chunk
        Returns:
            Dict with extracted entities
        """
        prompt = build_entity_extraction_prompt(text)
        self._apply_rate_limit()

        def call_llm():
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text

        response_text = self._retry_with_backoff(call_llm)
        entities, _ = self._parse_graph_extraction_response(response_text)

        try:
            if not entities:
                parsed = self._parse_json_response(response_text)
                if isinstance(parsed, dict):
                    entities = parsed.get("entities", [])
                elif isinstance(parsed, list):
                    entities = parsed

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
        prompt = build_relationship_extraction_prompt(text, entity_names)
        self._apply_rate_limit()

        def call_llm():
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            # Ensure response text is not None or empty
            text = response.text if response.text else ""
            return text

        response_text = self._retry_with_backoff(call_llm)

        # Check for empty response
        if not response_text or not response_text.strip():
            logger.warning(
                f"Empty response from LLM for relationship extraction (chunk {chunk_id})"
            )
            return {
                "chunk_id": chunk_id,
                "relationships": [],
                "status": "success",
            }

        # Parse graph extraction response - this extracts both entities and relationships
        extracted_entities, relationships = self._parse_graph_extraction_response(response_text)

        # Log if we got entity records instead of relationships
        if extracted_entities and not relationships:
            logger.warning(
                f"LLM returned {len(extracted_entities)} entity records but no relationships for chunk {chunk_id}. This may indicate the LLM didn't follow the relationship extraction format."
            )

        try:
            if entity_names:
                entity_name_set = {
                    name.strip().upper() for name in entity_names if name and isinstance(name, str)
                }
                if entity_name_set:
                    # Filter relationships to only include those between known entities
                    # Use case-insensitive matching for better accuracy
                    relationships = [
                        rel
                        for rel in relationships
                        if rel.get("source", "").strip().upper() in entity_name_set
                        and rel.get("target", "").strip().upper() in entity_name_set
                    ]

            # Fallback: Try JSON parsing if tuple parsing failed
            if not relationships:
                parsed = self._parse_json_response(response_text)
                if isinstance(parsed, dict):
                    relationships = parsed.get("relationships", [])
                elif isinstance(parsed, list):
                    relationships = parsed

            # Final validation: ensure relationships have required fields
            validated_relationships = []
            for rel in relationships:
                if isinstance(rel, dict) and rel.get("source") and rel.get("target"):
                    validated_relationships.append(rel)
                else:
                    logger.debug(f"Skipping invalid relationship record: {rel}")

            relationships = validated_relationships

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

    def extract_claims(
        self,
        text: str,
        entities: List[Dict],
        chunk_id: str,
        entity_specs: Optional[str] = None,
        claim_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract claims from text using GraphRAG claims extraction

        Args:
            text: Original text to extract claims from
            entities: Previously extracted entities
            chunk_id: Identifier for the text chunk
            entity_specs: Entity specification (optional, defaults to entity names)
            claim_description: Description of claims to extract (optional)

        Returns:
            Dict with extracted claims
        """
        try:
            # Use entity names as entity specs if not provided
            if not entity_specs and entities:
                entity_names = [e.get("name", "") for e in entities if e.get("name")]
                entity_specs = (
                    ", ".join(entity_names) if entity_names else "organization, person, event"
                )

            # Use consistent delimiters matching the prompt template defaults
            tuple_delimiter = "<|>"
            record_delimiter = "##"
            completion_delimiter = "<|COMPLETE|>"

            prompt = build_claims_extraction_prompt(
                input_text=text,
                entity_specs=entity_specs,
                claim_description=claim_description,
                tuple_delimiter=tuple_delimiter,
                record_delimiter=record_delimiter,
                completion_delimiter=completion_delimiter,
            )

            self._apply_rate_limit()

            def call_llm():
                model = genai.GenerativeModel(self.model_name)
                response = model.generate_content(prompt)
                return response.text

            response_text = self._retry_with_backoff(call_llm)

            # Parse claims from GraphRAG tuple format using matching delimiters
            claims = self._parse_claims_response(
                response_text,
                tuple_delimiter=tuple_delimiter,
                record_delimiter=record_delimiter,
                completion_delimiter=completion_delimiter,
            )

            return {
                "chunk_id": chunk_id,
                "claims": claims,
                "status": "success",
            }

        except Exception as e:
            logger.error(f"Claims extraction error: {e}")
            return {
                "chunk_id": chunk_id,
                "claims": [],
                "status": "error",
                "error": str(e),
            }

    def _parse_claims_response(
        self,
        response: str,
        tuple_delimiter: str = "<|>",
        record_delimiter: str = "##",
        completion_delimiter: str = "<|COMPLETE|>",
    ) -> List[Dict[str, Any]]:
        """
        Parse claims from GraphRAG tuple-based format

        Expected format:
        (SUBJECT<|>OBJECT<|>CLAIM_TYPE<|>STATUS<|>START_DATE<|>END_DATE<|>DESCRIPTION<|>SOURCE_TEXT)##
        (SUBJECT2<|>OBJECT2<|>CLAIM_TYPE2<|>STATUS2<|>START_DATE2<|>END_DATE2<|>DESCRIPTION2<|>SOURCE_TEXT2)##

        Args:
            response: LLM response text with claims in tuple format
            tuple_delimiter: Delimiter between tuple fields (default: "<|>")
            record_delimiter: Delimiter between records (default: "##")
            completion_delimiter: Completion marker (default: "<|COMPLETE|>")

        Returns:
            List of claim dictionaries
        """
        claims = []

        try:
            # Remove completion delimiter if present
            response = response.replace(completion_delimiter, "")

            # Remove markdown code blocks if present
            if "```" in response:
                import re

                response = re.sub(r"```[a-z]*\n", "", response)
                response = response.replace("```", "")

            response = response.strip()

            # Split by record delimiter
            claim_records = response.split(record_delimiter)

            for record in claim_records:
                record = record.strip()
                if not record:
                    continue

                # Skip markdown-style headers or non-tuple lines
                # These don't follow the tuple format (SUBJECT<|>OBJECT...)
                if not "(" in record or tuple_delimiter not in record:
                    # Log only if it's not a markdown header or empty line
                    if (
                        record
                        and not record.startswith("#")
                        and not record.startswith("-")
                        and len(record) > 5
                    ):
                        logger.debug(f"Skipping non-tuple claim record: {record[:100]}")
                    continue

                # Remove parentheses
                if record.startswith("(") and record.endswith(")"):
                    record = record[1:-1]
                elif record.startswith("("):
                    # Handle case where closing paren is missing
                    record = record[1:]

                # Split by tuple delimiter
                parts = record.split(tuple_delimiter)

                if len(parts) >= 8:  # Ensure we have all required fields
                    claim = {
                        "subject": parts[0].strip(),
                        "object": parts[1].strip(),
                        "claim_type": parts[2].strip(),
                        "status": parts[3].strip(),
                        "start_date": parts[4].strip() if parts[4].strip() != "NONE" else None,
                        "end_date": parts[5].strip() if parts[5].strip() != "NONE" else None,
                        "description": parts[6].strip(),
                        "source_text": parts[7].strip() if len(parts) > 7 else "",
                    }
                    claims.append(claim)
                elif len(parts) > 1:
                    # Log warning only for records that look like they should be claims but are malformed
                    logger.warning(
                        f"Malformed claim record (expected 8 fields, got {len(parts)}): {record[:100]}"
                    )

        except Exception as e:
            logger.error(f"Claims parsing error: {e}")

        logger.info(f"Parsed {len(claims)} claims from response")
        return claims

    async def batch_extract_claims(
        self,
        chunks_with_entities: List[Tuple[str, List[Dict], str]],
        entity_specs: Optional[str] = None,
        claim_description: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Batch extract claims from multiple chunks

        Args:
            chunks_with_entities: List of (text, entities, chunk_id) tuples
            entity_specs: Entity specification (optional)
            claim_description: Description of claims to extract (optional)

        Returns:
            List of extraction results
        """
        results = []
        for text, entities, chunk_id in chunks_with_entities:
            if entities:  # Only extract if there are entities
                result = self.extract_claims(
                    text=text,
                    entities=entities,
                    chunk_id=chunk_id,
                    entity_specs=entity_specs,
                    claim_description=claim_description,
                )
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
        prompt = build_query_classification_prompt(query)
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
        prompt = build_contextual_answer_prompt(query, context, citations)
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
        prompt = build_community_summary_prompt(entity_names, relationships_desc, sample_text)
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
            prompt = build_graph_community_summary_prompt(context)
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

    def summarize_community_batch(
        self,
        query: str,
        communities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Map phase: Summarize a batch of communities for a specific query

        Args:
            query: User's question
            communities: List of community dicts with id, summary, themes, size

        Returns:
            Dict with batch summary and relevant communities
        """
        try:
            # Format communities info
            communities_parts = []
            for comm in communities:
                comm_text = f"**Community {comm['community_id']}** (Level {comm.get('level', 0)}, {comm['size']} entities)"
                if comm.get("summary"):
                    comm_text += f"\n  Summary: {comm['summary']}"
                if comm.get("themes"):
                    comm_text += f"\n  Themes: {comm['themes']}"
                communities_parts.append(comm_text)

            communities_info = "\n\n".join(communities_parts)

            # Build prompt
            prompt = build_map_reduce_batch_summary_prompt(query, communities_info)

            # Apply rate limiting
            self._apply_rate_limit()

            # Call LLM
            def call_llm():
                model = genai.GenerativeModel(self.model_name)
                response = model.generate_content(prompt)
                return response.text

            response_text = self._retry_with_backoff(call_llm)

            # Parse JSON response
            result = self._parse_json_response(response_text)

            return {
                "status": "success",
                "batch_summary": result.get("summary", ""),
                "key_points": result.get("key_points", []),
                "relevant_communities": result.get("relevant_communities", []),
                "confidence": result.get("confidence", "medium"),
            }

        except Exception as e:
            logger.error(f"Batch summarization failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "batch_summary": "",
                "key_points": [],
                "relevant_communities": [],
                "confidence": "low",
            }

    def synthesize_final_answer(
        self,
        query: str,
        intermediate_summaries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Reduce phase: Synthesize intermediate summaries into final answer

        Args:
            query: User's question
            intermediate_summaries: List of batch summaries from Map phase

        Returns:
            Dict with final answer and metadata
        """
        try:
            # Format intermediate summaries
            summaries_parts = []
            for i, summary in enumerate(intermediate_summaries, 1):
                if summary.get("status") == "success":
                    text = f"**Batch {i}** (Confidence: {summary.get('confidence', 'medium')})"
                    text += f"\n{summary.get('batch_summary', '')}"
                    if summary.get("key_points"):
                        text += "\nKey Points:\n" + "\n".join(
                            [f"- {p}" for p in summary["key_points"]]
                        )
                    if summary.get("relevant_communities"):
                        text += f"\nRelevant Communities: {', '.join(map(str, summary['relevant_communities']))}"
                    summaries_parts.append(text)

            summaries_text = "\n\n".join(summaries_parts)

            # Build prompt
            prompt = build_map_reduce_final_synthesis_prompt(query, summaries_text)

            # Apply rate limiting
            self._apply_rate_limit()

            # Call LLM
            def call_llm():
                model = genai.GenerativeModel(self.model_name)
                response = model.generate_content(prompt)
                return response.text

            response_text = self._retry_with_backoff(call_llm)

            # Parse JSON response
            result = self._parse_json_response(response_text)

            return {
                "status": "success",
                "answer": result.get("answer", ""),
                "key_insights": result.get("key_insights", []),
                "supporting_communities": result.get("supporting_communities", []),
                "confidence_score": str(result.get("confidence_score", "0.7")),
                "limitations": result.get("limitations", ""),
            }

        except Exception as e:
            logger.error(f"Final synthesis failed: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "answer": "Failed to synthesize final answer from intermediate summaries.",
                "key_insights": [],
                "supporting_communities": [],
                "confidence_score": "0.0",
                "limitations": str(e),
            }


# Export singleton instance
llm_service = LLMService()
