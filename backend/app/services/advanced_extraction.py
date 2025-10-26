"""
Advanced extraction service with few-shot learning and context awareness
"""

import json
import logging
from typing import Any, Dict, List, Optional

import google.generativeai as genai

from app.config import get_settings
from app.db.neo4j import get_neo4j_session

logger = logging.getLogger(__name__)

settings = get_settings()
genai.configure(api_key=settings.GOOGLE_API_KEY)


class AdvancedExtractionService:
    """Service for advanced entity and relationship extraction"""

    def __init__(self):
        """Initialize advanced extraction service"""
        self.session = None
        self.model_name = "gemini-2.5-flash"

        # Few-shot examples for extraction
        self.few_shot_examples = {
            "entity": """
Examples of entity extraction:
1. Text: "Apple Inc. was founded by Steve Jobs in 1976."
   Output: [{"name": "Apple Inc.", "type": "ORGANIZATION", "context": "Founded company"}, 
            {"name": "Steve Jobs", "type": "PERSON", "context": "Founder"}]

2. Text: "The Python programming language was created by Guido van Rossum."
   Output: [{"name": "Python", "type": "PRODUCT", "context": "Programming language"},
            {"name": "Guido van Rossum", "type": "PERSON", "context": "Creator"}]
""",
            "relationship": """
Examples of relationship extraction:
1. Text: "Microsoft acquired LinkedIn for $26.2 billion in 2016."
   Output: [{"source": "Microsoft", "target": "LinkedIn", "type": "ACQUIRED", "description": "Microsoft acquired LinkedIn for $26.2 billion"}]

2. Text: "OpenAI developed GPT-3, an advanced language model."
   Output: [{"source": "OpenAI", "target": "GPT-3", "type": "DEVELOPED", "description": "OpenAI developed GPT-3"}]
""",
        }

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

            prompt = f"""{self.few_shot_examples['entity']}

Now extract entities from the following text. Only extract the specified entity types: {entity_types_str}

Text: "{text}"

Return a JSON array with entities in this format:
[{{"name": "...", "type": "...", "context": "..."}}]

Only return valid JSON, no additional text.
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
            prompt = f"""Identify and resolve coreferences (pronouns, aliases, etc.) in the following text.
For each pronoun or reference, identify which entity it refers to.

Text: "{text}"

Return a JSON object with coreference resolutions:
{{
    "coreferences": [
        {{"mention": "...", "referent": "...", "type": "pronoun|alias|abbreviation"}}
    ],
    "entities": ["..."] // list of main entities
}}

Only return valid JSON.
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
            prompt = f"""Extract all attributes, properties, and characteristics of the entity "{entity_name}" from the following text:

Text: "{text}"

Return a JSON object:
{{
    "entity": "{entity_name}",
    "attributes": {{
        "description": "...",
        "properties": ["..."],
        "relationships": ["..."],
        "roles": ["..."],
        "characteristics": ["..."]
    }}
}}

Only return valid JSON.
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
            prompt = f"""Extract all events, actions, and temporal information from the following text:

Text: "{text}"

Return a JSON object:
{{
    "events": [
        {{
            "event": "...",
            "participants": ["..."],
            "date": "...",
            "location": "...",
            "description": "...",
            "importance": "high|medium|low"
        }}
    ]
}}

Only return valid JSON.
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

            prompt = f"""Generate answers to the following query from different perspectives:

Query: "{query}"

Context: "{context}"

Perspectives to consider: {", ".join(perspectives)}

Return a JSON object:
{{
    "query": "{query}",
    "perspectives": {{
        "technical": {{"answer": "...", "confidence": 0.0-1.0}},
        "business": {{"answer": "...", "confidence": 0.0-1.0}},
        "social": {{"answer": "...", "confidence": 0.0-1.0}},
        "ethical": {{"answer": "...", "confidence": 0.0-1.0}}
    }},
    "synthesis": "..."
}}

Only return valid JSON.
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
