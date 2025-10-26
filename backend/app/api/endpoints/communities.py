"""
Community and retrieval API endpoints for Phase 2 advanced features
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException

from app.services.community_detection import community_detection_service
from app.services.community_summarization import community_summarization_service
from app.services.retrieval_service import retrieval_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["communities"])


# Community Detection Endpoints


@router.post("/communities/detect")
async def detect_communities() -> Dict:
    """
    Detect communities in the knowledge graph using Leiden algorithm

    Returns:
        Dictionary with detected communities
    """
    try:
        result = community_detection_service.detect_communities()
        return result
    except Exception as e:
        logger.error(f"Community detection error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communities/statistics")
async def get_community_statistics() -> Dict:
    """
    Get statistics about detected communities

    Returns:
        Dictionary with community statistics
    """
    try:
        result = community_detection_service.get_community_statistics()
        return result
    except Exception as e:
        logger.error(f"Community statistics error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communities/{community_id}/members")
async def get_community_members(community_id: int) -> Dict:
    """
    Get members of a specific community

    Args:
        community_id: Community ID

    Returns:
        Dictionary with community members
    """
    try:
        result = community_detection_service.get_community_members(community_id)
        return result
    except Exception as e:
        logger.error(f"Get community members error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communities/{source_entity}/path/{target_entity}")
async def get_community_path(
    source_entity: str, target_entity: str, max_depth: int = 3
) -> Dict:
    """
    Find path between two entities considering community structure

    Args:
        source_entity: Source entity name
        target_entity: Target entity name
        max_depth: Maximum path depth

    Returns:
        Dictionary with path information
    """
    try:
        result = community_detection_service.get_entities_in_community_path(
            source_entity, target_entity, max_depth
        )
        return result
    except Exception as e:
        logger.error(f"Get community path error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Community Summarization Endpoints


@router.post("/communities/{community_id}/summarize")
async def summarize_community(community_id: int) -> Dict:
    """
    Generate summary for a specific community

    Args:
        community_id: Community ID

    Returns:
        Dictionary with community summary
    """
    try:
        result = community_summarization_service.summarize_community(community_id)
        return result
    except Exception as e:
        logger.error(f"Community summarization error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/communities/summarize-all")
async def summarize_all_communities() -> Dict:
    """
    Generate summaries for all detected communities

    Returns:
        Dictionary with all community summaries
    """
    try:
        result = community_summarization_service.summarize_all_communities()
        return result
    except Exception as e:
        logger.error(f"Summarize all communities error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communities/{community_id}/summary")
async def get_community_summary(community_id: int) -> Dict:
    """
    Get previously generated summary for a community

    Args:
        community_id: Community ID

    Returns:
        Dictionary with community summary
    """
    try:
        result = community_summarization_service.get_community_summary(community_id)
        return result
    except Exception as e:
        logger.error(f"Get community summary error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/communities/{c1}/compare/{c2}")
async def compare_communities(c1: int, c2: int) -> Dict:
    """
    Compare two communities and find connections

    Args:
        c1: First community ID
        c2: Second community ID

    Returns:
        Dictionary with community comparison
    """
    try:
        result = community_summarization_service.compare_communities(c1, c2)
        return result
    except Exception as e:
        logger.error(f"Community comparison error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Multi-level Retrieval Endpoints


@router.post("/retrieve/local")
async def retrieve_local(entity: str, hop_limit: int = 1) -> Dict:
    """
    Retrieve local context around an entity

    Args:
        entity: Entity name
        hop_limit: Number of hops

    Returns:
        Dictionary with local context
    """
    try:
        result = retrieval_service.retrieve_local_context(entity, hop_limit)
        return result
    except Exception as e:
        logger.error(f"Local retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve/community")
async def retrieve_community(entity: str, include_summaries: bool = True) -> Dict:
    """
    Retrieve community context around an entity

    Args:
        entity: Entity name
        include_summaries: Whether to include community summaries

    Returns:
        Dictionary with community context
    """
    try:
        result = retrieval_service.retrieve_community_context(
            entity, include_summaries
        )
        return result
    except Exception as e:
        logger.error(f"Community retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retrieve/global")
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
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve/hierarchical")
async def hierarchical_search(
    query: str,
    retrieval_levels: List[str] = None,
    combine_results: bool = True,
) -> Dict:
    """
    Perform hierarchical search combining multiple retrieval levels

    Args:
        query: Query string
        retrieval_levels: List of retrieval levels to use
        combine_results: Whether to combine results

    Returns:
        Dictionary with hierarchical search results
    """
    try:
        if retrieval_levels is None:
            retrieval_levels = ["local", "community", "global"]

        result = retrieval_service.hierarchical_search(
            query, retrieval_levels, combine_results
        )
        return result
    except Exception as e:
        logger.error(f"Hierarchical search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retrieve/adaptive")
async def adaptive_retrieval(query: str, query_type: Optional[str] = None) -> Dict:
    """
    Adaptively select retrieval strategy based on query type

    Args:
        query: User query
        query_type: Optional pre-classified query type

    Returns:
        Dictionary with adaptive retrieval results
    """
    try:
        result = retrieval_service.adaptive_retrieval(query, query_type)
        return result
    except Exception as e:
        logger.error(f"Adaptive retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
