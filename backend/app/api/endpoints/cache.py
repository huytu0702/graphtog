"""
Cache management API endpoints
"""

import logging
from typing import Dict

from fastapi import APIRouter, HTTPException

from app.services.cache_service import cache_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cache"])


@router.get("/stats")
async def get_cache_stats() -> Dict:
    """
    Get cache statistics

    Returns:
        Dictionary with Redis cache stats
    """
    try:
        stats = cache_service.get_cache_stats()
        return stats
    except Exception as e:
        logger.error(f"Cache stats error: {str(e)}")
        return {"status": "error", "message": str(e), "stats": {}}


@router.post("/clear-all")
async def clear_all_caches() -> Dict:
    """
    Clear all application caches

    Returns:
        Dictionary with number of entries cleared
    """
    try:
        count = cache_service.invalidate_all_caches()
        return {
            "status": "success",
            "cleared_entries": count,
        }
    except Exception as e:
        logger.error(f"Clear all caches error: {str(e)}")
        return {"status": "error", "message": str(e), "cleared_entries": 0}


@router.post("/clear/{cache_type}")
async def clear_cache_type(cache_type: str) -> Dict:
    """
    Clear cache by type

    Args:
        cache_type: Type of cache (entity, community, query, retrieval)

    Returns:
        Dictionary with number of entries cleared
    """
    try:
        pattern = f"{cache_type}:*"
        count = cache_service.clear_cache_pattern(pattern)
        return {
            "status": "success",
            "cache_type": cache_type,
            "cleared_entries": count,
        }
    except Exception as e:
        logger.error(f"Clear cache type error: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "cache_type": cache_type,
            "cleared_entries": 0,
        }


@router.delete("/key/{key}")
async def delete_cache_key(key: str) -> Dict:
    """
    Delete specific cache key

    Args:
        key: Cache key to delete

    Returns:
        Dictionary with deletion status
    """
    try:
        success = cache_service.delete_cache(key)
        return {
            "status": "success" if success else "not_found",
            "key": key,
        }
    except Exception as e:
        logger.error(f"Delete cache key error: {str(e)}")
        return {"status": "error", "message": str(e), "key": key}
