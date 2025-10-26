"""
Advanced features API endpoints for Phase 2
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.services.advanced_extraction import advanced_extraction_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["advanced"])


# Advanced Extraction Endpoints


@router.post("/extract/few-shot")
async def extract_with_few_shot(
    text: str, entity_types: Optional[List[str]] = None
) -> Dict:
    """
    Extract entities using few-shot learning

    Args:
        text: Text to extract from
        entity_types: Optional list of entity types

    Returns:
        Dictionary with extracted entities
    """
    try:
        result = advanced_extraction_service.extract_with_few_shot(text, entity_types)
        return result
    except Exception as e:
        logger.error(f"Few-shot extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract/coreferences")
async def resolve_coreferences(text: str) -> Dict:
    """
    Resolve coreferences in text

    Args:
        text: Text to resolve coreferences

    Returns:
        Dictionary with coreference resolutions
    """
    try:
        result = advanced_extraction_service.resolve_coreferences(text)
        return result
    except Exception as e:
        logger.error(f"Coreference resolution error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract/attributes")
async def extract_attributes(entity_name: str, text: str) -> Dict:
    """
    Extract attributes and properties of an entity

    Args:
        entity_name: Entity name
        text: Context text

    Returns:
        Dictionary with entity attributes
    """
    try:
        result = advanced_extraction_service.extract_attributes(entity_name, text)
        return result
    except Exception as e:
        logger.error(f"Attribute extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/extract/events")
async def extract_events(text: str) -> Dict:
    """
    Extract events and temporal information

    Args:
        text: Text to extract events from

    Returns:
        Dictionary with extracted events
    """
    try:
        result = advanced_extraction_service.extract_events(text)
        return result
    except Exception as e:
        logger.error(f"Event extraction error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Multi-Perspective Analysis Endpoints


@router.post("/analyze/multi-perspective")
async def generate_multi_perspective_answer(
    query: str, context: str, perspectives: Optional[List[str]] = None
) -> Dict:
    """
    Generate answer from multiple perspectives

    Args:
        query: User query
        context: Retrieved context
        perspectives: Optional list of perspectives

    Returns:
        Dictionary with multi-perspective answers
    """
    try:
        result = advanced_extraction_service.generate_multi_perspective_answer(
            query, context, perspectives
        )
        return result
    except Exception as e:
        logger.error(f"Multi-perspective analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
