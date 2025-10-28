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


@router.post("/detect")
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


@router.get("/statistics")
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


@router.get("/{community_id}/members")
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


@router.get("/{source_entity}/path/{target_entity}")
async def find_path(source_entity: str, target_entity: str, max_depth: int = 3) -> Dict:
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


@router.post("/{community_id}/summarize")
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


@router.post("/summarize-all")
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


@router.get("/{community_id}/summary")
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


@router.get("/{c1}/compare/{c2}")
async def compare_communities(c1: int, c2: int) -> Dict:
    """
    Compare two communities

    Args:
        c1: ID of first community
        c2: ID of second community

    Returns:
        Dictionary with comparison results
    """
    try:
        result = community_detection_service.compare_communities(c1, c2)
        return result
    except Exception as e:
        logger.error(f"Community comparison error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Retrieval Endpoints - MOVED TO retrieval.py - DO NOT USE THESE

# Previous retrieval endpoints have been moved to a separate retrieval.py module
# to better organize the API structure.
# See /api/retrieve/* endpoints instead.
