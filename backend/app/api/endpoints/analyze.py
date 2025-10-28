"""
Analysis API endpoints for advanced reasoning
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.advanced_extraction import advanced_extraction_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["analysis"])


# Request models
class MultiPerspectiveRequest(BaseModel):
    query: str
    context: str
    perspectives: Optional[List[str]] = None


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
