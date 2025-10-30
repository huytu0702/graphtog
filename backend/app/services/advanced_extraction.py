"""
Advanced extraction service with few-shot learning and context awareness
"""

import json
import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from app.config import get_settings
from app.db.neo4j import get_neo4j_session
from app.services.prompt import (
    FEW_SHOT_EXAMPLES,
    build_attribute_extraction_prompt,
    build_coreference_prompt,
    build_event_extraction_prompt,
    build_few_shot_entity_prompt,
    build_multi_perspective_prompt,
)

logger = logging.getLogger(__name__)

settings = get_settings()
genai.configure(api_key=settings.GOOGLE_API_KEY)


class AdvancedExtractionService:
    """Service for advanced entity and relationship extraction"""

    def __init__(self):
        """Initialize advanced extraction service"""
        self.session = None
        self.model_name = "gemini-2.5-flash"
        self.few_shot_examples = FEW_SHOT_EXAMPLES

    def get_session(self):
        """Get or create Neo4j session"""
        if not self.session:
            self.session = get_neo4j_session()
        return self.session

    def extract_with_few_shot(
        self, text: str, entity_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract entities using few-shot learning

        Args:
            text: Text to extract from
            entity_types: Optional list of entity types to extract

        Returns:
            Dictionary with extracted entities
        """
        try:
            entity_types_str = (
                ", ".join(entity_types)
                if entity_types
                else "PERSON, ORGANIZATION, LOCATION, CONCEPT, EVENT, PRODUCT, OTHER"
            )

            prompt = build_few_shot_entity_prompt(
                text,
                entity_types_str,
                self.few_shot_examples["entity"],
            )

            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)

            try:
                result_text = response.text.strip()
                if result_text.startswith("```"):
                    result_text = result_text.split("```")[1]
                    if result_text.startswith("json"):
                        result_text = result_text[4:]
                    result_text = result_text.strip()

                entities = json.loads(result_text)
                return {
                    "status": "success",
                    "entities": entities,
                    "extraction_type": "few-shot",
                }
            except json.JSONDecodeError:
                logger.warning("Could not parse few-shot extraction JSON")
                return {"status": "error", "message": "Invalid JSON response"}

        except Exception as e:
            logger.error(f"Few-shot extraction failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def resolve_coreferences(self, text: str) -> Dict[str, Any]:
        """
        Resolve coreferences in text (pronouns to entities)

        Args:
            text: Text to resolve coreferences in

        Returns:
            Dictionary with coreference resolutions
        """
        try:
            prompt = build_coreference_prompt(text)

            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)

            try:
                result_text = response.text.strip()
                if result_text.startswith("```"):
                    result_text = result_text.split("```")[1]
                    if result_text.startswith("json"):
                        result_text = result_text[4:]
                    result_text = result_text.strip()

                result = json.loads(result_text)
                return {
                    "status": "success",
                    "coreferences": result.get("coreferences", []),
                    "entities": result.get("entities", []),
                }
            except json.JSONDecodeError:
                logger.warning("Could not parse coreference resolution JSON")
                return {"status": "error", "message": "Invalid JSON response"}

        except Exception as e:
            logger.error(f"Coreference resolution failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def extract_attributes(self, entity_name: str, text: str) -> Dict[str, Any]:
        """
        Extract attributes and properties of an entity

        Args:
            entity_name: Entity name to extract attributes for
            text: Context text

        Returns:
            Dictionary with entity attributes
        """
        try:
            prompt = build_attribute_extraction_prompt(entity_name, text)

            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)

            try:
                result_text = response.text.strip()
                if result_text.startswith("```"):
                    result_text = result_text.split("```")[1]
                    if result_text.startswith("json"):
                        result_text = result_text[4:]
                    result_text = result_text.strip()

                result = json.loads(result_text)
                return {
                    "status": "success",
                    "entity": result.get("entity"),
                    "attributes": result.get("attributes", {}),
                }
            except json.JSONDecodeError:
                logger.warning("Could not parse attributes JSON")
                return {"status": "error", "message": "Invalid JSON response"}

        except Exception as e:
            logger.error(f"Attribute extraction failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def extract_events(self, text: str) -> Dict[str, Any]:
        """
        Extract events and temporal information

        Args:
            text: Text to extract events from

        Returns:
            Dictionary with extracted events
        """
        try:
            prompt = build_event_extraction_prompt(text)

            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)

            try:
                result_text = response.text.strip()
                if result_text.startswith("```"):
                    result_text = result_text.split("```")[1]
                    if result_text.startswith("json"):
                        result_text = result_text[4:]
                    result_text = result_text.strip()

                result = json.loads(result_text)
                return {
                    "status": "success",
                    "events": result.get("events", []),
                }
            except json.JSONDecodeError:
                logger.warning("Could not parse events JSON")
                return {"status": "error", "message": "Invalid JSON response"}

        except Exception as e:
            logger.error(f"Event extraction failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def generate_multi_perspective_answer(
        self, query: str, context: str, perspectives: List[str] = None
    ) -> Dict[str, Any]:
        """
        Generate answer from multiple perspectives

        Args:
            query: User query
            context: Retrieved context
            perspectives: List of perspectives to consider

        Returns:
            Dictionary with multi-perspective answers
        """
        try:
            if perspectives is None:
                perspectives = ["technical", "business", "social", "ethical"]

            prompt = build_multi_perspective_prompt(query, context, perspectives)

            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)

            try:
                result_text = response.text.strip()
                if result_text.startswith("```"):
                    result_text = result_text.split("```")[1]
                    if result_text.startswith("json"):
                        result_text = result_text[4:]
                    result_text = result_text.strip()

                result = json.loads(result_text)
                return {
                    "status": "success",
                    "perspectives": result.get("perspectives", {}),
                    "synthesis": result.get("synthesis", ""),
                }
            except json.JSONDecodeError:
                logger.warning("Could not parse multi-perspective JSON")
                return {"status": "error", "message": "Invalid JSON response"}

        except Exception as e:
            logger.error(f"Multi-perspective generation failed: {str(e)}")
            return {"status": "error", "message": str(e)}


# Singleton instance
advanced_extraction_service = AdvancedExtractionService()
