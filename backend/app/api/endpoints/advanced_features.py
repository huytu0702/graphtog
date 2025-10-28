"""
Advanced features API endpoints for Phase 2
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.advanced_extraction import advanced_extraction_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["advanced"])


# Request models
class FewShotExtractionRequest(BaseModel):
    text: str
    entity_types: Optional[List[str]] = None


class CoreferenceResolutionRequest(BaseModel):
    text: str


class AttributeExtractionRequest(BaseModel):
    entity_name: str
    text: str


class EventExtractionRequest(BaseModel):
    text: str


class MultiPerspectiveRequest(BaseModel):
    query: str
    context: str
    perspectives: Optional[List[str]] = None


# Advanced Extraction Endpoints


@router.post("/few-shot")
async def extract_with_few_shot(request: FewShotExtractionRequest) -> Dict:
    """
    Extract entities using few-shot learning

    Args:
        request: FewShotExtractionRequest

    Returns:
        Dictionary with extracted entities
    """
    try:
        result = advanced_extraction_service.extract_with_few_shot(
            request.text, request.entity_types
        )
        return result
    except Exception as e:
        logger.error(f"Few-shot extraction error: {str(e)}")
        return {"status": "error", "message": str(e), "entities": []}


@router.post("/coreferences")
async def resolve_coreferences(request: CoreferenceResolutionRequest) -> Dict:
    """
    Resolve coreferences in text

    Args:
        request: CoreferenceResolutionRequest

    Returns:
        Dictionary with coreference resolutions
    """
    try:
        result = advanced_extraction_service.resolve_coreferences(request.text)
        return result
    except Exception as e:
        logger.error(f"Coreference resolution error: {str(e)}")
        return {"status": "error", "message": str(e), "coreferences": []}


@router.post("/attributes")
async def extract_attributes(request: AttributeExtractionRequest) -> Dict:
    """
    Extract attributes and properties of an entity

    Args:
        request: AttributeExtractionRequest

    Returns:
        Dictionary with entity attributes
    """
    try:
        result = advanced_extraction_service.extract_attributes(request.entity_name, request.text)
        return result
    except Exception as e:
        logger.error(f"Attribute extraction error: {str(e)}")
        return {"status": "error", "message": str(e), "attributes": []}


@router.post("/events")
async def extract_events(request: EventExtractionRequest) -> Dict:
    """
    Extract events and temporal information

    Args:
        request: EventExtractionRequest

    Returns:
        Dictionary with extracted events
    """
    try:
        result = advanced_extraction_service.extract_events(request.text)
        return result
    except Exception as e:
        logger.error(f"Event extraction error: {str(e)}")
        return {"status": "error", "message": str(e), "events": []}


# Multi-Perspective Analysis Endpoints
# Note: This endpoint is under /api/extract but tests expect /api/analyze
# This is a routing quirk - the actual implementation should have this in a separate router


@router.post("/multi-perspective")
async def generate_multi_perspective_answer(request: MultiPerspectiveRequest) -> Dict:
    """
    Generate answer from multiple perspectives

    Args:
        request: MultiPerspectiveRequest

    Returns:
        Dictionary with multi-perspective answers
    """
    try:
        result = advanced_extraction_service.generate_multi_perspective_answer(
            request.query, request.context, request.perspectives
        )
        return result
    except Exception as e:
        logger.error(f"Multi-perspective analysis error: {str(e)}")
        return {"status": "error", "message": str(e), "answers": []}
