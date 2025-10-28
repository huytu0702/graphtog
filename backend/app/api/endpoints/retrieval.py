"""
Retrieval API endpoints for graph-based context retrieval
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.retrieval_service import retrieval_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["retrieval"])


# Request models
class LocalRetrievalRequest(BaseModel):
    entity: str
    hop_limit: int = 1


class CommunityRetrievalRequest(BaseModel):
    entity: str
    include_summaries: bool = True


class HierarchicalSearchRequest(BaseModel):
    query: str
    retrieval_levels: List[str] = None
    combine_results: bool = True


class AdaptiveRetrievalRequest(BaseModel):
    query: str
    query_type: Optional[str] = None


@router.post("/local")
async def retrieve_local(request: LocalRetrievalRequest) -> Dict:
    """
    Retrieve local context around an entity

    Args:
        request: LocalRetrievalRequest with entity and hop_limit

    Returns:
        Dictionary with local context
    """
    try:
        result = retrieval_service.retrieve_local_context(request.entity, request.hop_limit)
        return result
    except Exception as e:
        logger.error(f"Local retrieval error: {str(e)}")
        return {"status": "error", "message": str(e), "data": []}


@router.post("/community")
async def retrieve_community(request: CommunityRetrievalRequest) -> Dict:
    """
    Retrieve community context around an entity

    Args:
        request: CommunityRetrievalRequest

    Returns:
        Dictionary with community context
    """
    try:
        result = retrieval_service.retrieve_community_context(
            request.entity, request.include_summaries
        )
        return result
    except Exception as e:
        logger.error(f"Community retrieval error: {str(e)}")
        return {"status": "error", "message": str(e), "data": []}


@router.get("/global")
async def retrieve_global() -> Dict:
    """
    Retrieve global context (all communities)

    Returns:
        Dictionary with global context
    """
    try:
        result = retrieval_service.retrieve_global_context()
        return result
    except Exception as e:
        logger.error(f"Global retrieval error: {str(e)}")
        return {"status": "error", "message": str(e), "data": []}


@router.post("/hierarchical")
async def hierarchical_search(request: HierarchicalSearchRequest) -> Dict:
    """
    Perform hierarchical search combining multiple retrieval levels

    Args:
        request: HierarchicalSearchRequest

    Returns:
        Dictionary with hierarchical search results
    """
    try:
        retrieval_levels = request.retrieval_levels or ["local", "community", "global"]
        result = retrieval_service.hierarchical_search(
            request.query, retrieval_levels, request.combine_results
        )
        return result
    except Exception as e:
        logger.error(f"Hierarchical search error: {str(e)}")
        return {"status": "error", "message": str(e), "data": []}


@router.post("/adaptive")
async def adaptive_retrieval(request: AdaptiveRetrievalRequest) -> Dict:
    """
    Adaptively select retrieval strategy based on query type

    Args:
        request: AdaptiveRetrievalRequest

    Returns:
        Dictionary with adaptive retrieval results
    """
    try:
        result = retrieval_service.adaptive_retrieval(request.query, request.query_type)
        return result
    except Exception as e:
        logger.error(f"Adaptive retrieval error: {str(e)}")
        return {"status": "error", "message": str(e), "data": []}
