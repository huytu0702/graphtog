"""
Graph visualization API endpoints
"""

import logging
from typing import Dict

from fastapi import APIRouter, HTTPException

from app.services.visualization_service import visualization_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["visualization"])


@router.get("/entity-graph")
async def get_entity_graph(limit: int = 100, include_communities: bool = True) -> Dict:
    """
    Get entity graph for visualization

    Args:
        limit: Maximum number of entities
        include_communities: Whether to include community nodes

    Returns:
        Dictionary with nodes and edges for Cytoscape.js
    """
    try:
        result = visualization_service.get_entity_graph(limit, include_communities)
        return result
    except Exception as e:
        logger.error(f"Entity graph visualization error: {str(e)}")
        return {"status": "error", "message": str(e), "elements": []}


@router.get("/community-graph")
async def get_community_graph(include_members: bool = True, max_members: int = 10) -> Dict:
    """
    Get community graph for visualization

    Args:
        include_members: Whether to include entity members
        max_members: Maximum members per community

    Returns:
        Dictionary with community graph data
    """
    try:
        result = visualization_service.get_community_graph(include_members, max_members)
        return result
    except Exception as e:
        logger.error(f"Community graph visualization error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hierarchical-graph")
async def get_hierarchical_graph() -> Dict:
    """
    Get hierarchical graph (documents -> entities -> communities)

    Returns:
        Dictionary with hierarchical graph data
    """
    try:
        result = visualization_service.get_hierarchical_graph()
        return result
    except Exception as e:
        logger.error(f"Hierarchical graph visualization error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ego-graph/{entity_id}")
async def get_ego_graph(entity_id: str, hop_limit: int = 2) -> Dict:
    """
    Get ego graph centered on an entity

    Args:
        entity_id: Entity ID
        hop_limit: Number of hops to include

    Returns:
        Dictionary with ego graph data
    """
    try:
        result = visualization_service.get_ego_graph(entity_id, hop_limit)
        return result
    except Exception as e:
        logger.error(f"Ego graph visualization error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
