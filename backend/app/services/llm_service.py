"""
LLM service for entity and relationship extraction
"""

import logging
from typing import Dict, List, Any

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Import Google Generative AI only if API key is configured
if settings.GEMINI_API_KEY:
    import google.generativeai as genai
    genai.configure(api_key=settings.GEMINI_API_KEY)
    model = genai.GenerativeModel(settings.GEMINI_MODEL)
else:
    logger.warning("GEMINI_API_KEY not configured, LLM features will be disabled")
    model = None


def extract_entities_and_relationships(text: str) -> Dict[str, Any]:
    """
    Extract entities and relationships from text using LLM
    
    Args:
        text: Input text to analyze
        
    Returns:
        Dictionary containing extracted entities and relationships
    """
    if not model:
        logger.error("LLM model not configured, returning empty result")
        return {"entities": [], "relationships": []}
    
    # Prompt for entity and relationship extraction
    prompt = f"""
    Analyze the following text and extract named entities and their relationships:
    
    TEXT: {text}
    
    Please return the result in the following JSON format:
    {{
        "entities": [
            {{"name": "entity_name", "type": "entity_type", "description": "entity_description"}}
        ],
        "relationships": [
            {{"source": "source_entity_name", "target": "target_entity_name", "type": "relationship_type", "description": "relationship_description"}}
        ]
    }}
    
    Only return the JSON, no additional text.
    """
    
    try:
        response = model.generate_content(prompt)
        
        # Parse the response as JSON
        import json
        result = json.loads(response.text.strip())
        
        logger.info(f"Extracted {len(result.get('entities', []))} entities and {len(result.get('relationships', []))} relationships")
        return result
        
    except Exception as e:
        logger.error(f"Error extracting entities and relationships: {str(e)}")
        # Return empty result in case of error
        return {"entities": [], "relationships": []}