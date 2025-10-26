"""
Redis caching service for performance optimization
"""

import json
import logging
from typing import Any, Dict, Optional

import redis

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class CacheService:
    """Service for Redis-based caching"""

    def __init__(self):
        """Initialize cache service"""
        self.redis_client = None
        self.default_ttl = 3600  # 1 hour default TTL

    def get_redis_client(self) -> redis.Redis:
        """Get or create Redis connection"""
        if not self.redis_client:
            try:
                self.redis_client = redis.Redis(
                    host=settings.REDIS_HOST or "localhost",
                    port=settings.REDIS_PORT or 6379,
                    db=0,
                    decode_responses=True,
                )
                # Test connection
                self.redis_client.ping()
                logger.info("Connected to Redis successfully")
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {str(e)}")
                return None

        return self.redis_client

    def set_cache(
        self, key: str, value: Any, ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            client = self.get_redis_client()
            if not client:
                return False

            ttl = ttl or self.default_ttl
            json_value = json.dumps(value)
            client.setex(key, ttl, json_value)
            logger.debug(f"Cached: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.warning(f"Cache set failed for {key}: {str(e)}")
            return False

    def get_cache(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            client = self.get_redis_client()
            if not client:
                return None

            value = client.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)

            logger.debug(f"Cache miss: {key}")
            return None

        except Exception as e:
            logger.warning(f"Cache get failed for {key}: {str(e)}")
            return None

    def delete_cache(self, key: str) -> bool:
        """
        Delete value from cache

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        try:
            client = self.get_redis_client()
            if not client:
                return False

            client.delete(key)
            logger.debug(f"Cache deleted: {key}")
            return True

        except Exception as e:
            logger.warning(f"Cache delete failed for {key}: {str(e)}")
            return False

    def clear_cache_pattern(self, pattern: str) -> int:
        """
        Clear cache by pattern

        Args:
            pattern: Key pattern (e.g., "entity:*")

        Returns:
            Number of keys deleted
        """
        try:
            client = self.get_redis_client()
            if not client:
                return 0

            keys = client.keys(pattern)
            if keys:
                deleted = client.delete(*keys)
                logger.debug(f"Cleared {deleted} cache keys matching {pattern}")
                return deleted

            return 0

        except Exception as e:
            logger.warning(f"Cache clear pattern failed for {pattern}: {str(e)}")
            return 0

    def cache_entity(self, entity_id: str, entity_data: Dict) -> bool:
        """Cache entity data"""
        return self.set_cache(f"entity:{entity_id}", entity_data, ttl=1800)

    def get_cached_entity(self, entity_id: str) -> Optional[Dict]:
        """Get cached entity data"""
        return self.get_cache(f"entity:{entity_id}")

    def cache_community(self, community_id: int, community_data: Dict) -> bool:
        """Cache community data"""
        return self.set_cache(f"community:{community_id}", community_data, ttl=1800)

    def get_cached_community(self, community_id: int) -> Optional[Dict]:
        """Get cached community data"""
        return self.get_cache(f"community:{community_id}")

    def cache_query_result(self, query_id: str, result: Dict) -> bool:
        """Cache query result"""
        return self.set_cache(f"query:{query_id}", result, ttl=3600)

    def get_cached_query_result(self, query_id: str) -> Optional[Dict]:
        """Get cached query result"""
        return self.get_cache(f"query:{query_id}")

    def cache_retrieval_result(
        self, retrieval_id: str, result: Dict, ttl: int = 3600
    ) -> bool:
        """Cache retrieval result"""
        return self.set_cache(f"retrieval:{retrieval_id}", result, ttl=ttl)

    def get_cached_retrieval_result(self, retrieval_id: str) -> Optional[Dict]:
        """Get cached retrieval result"""
        return self.get_cache(f"retrieval:{retrieval_id}")

    def invalidate_entity_cache(self, entity_id: str) -> bool:
        """Invalidate entity cache"""
        return self.delete_cache(f"entity:{entity_id}")

    def invalidate_community_cache(self, community_id: int) -> bool:
        """Invalidate community cache"""
        return self.delete_cache(f"community:{community_id}")

    def invalidate_all_caches(self) -> int:
        """Clear all application caches"""
        count = 0
        count += self.clear_cache_pattern("entity:*")
        count += self.clear_cache_pattern("community:*")
        count += self.clear_cache_pattern("query:*")
        count += self.clear_cache_pattern("retrieval:*")
        logger.info(f"Invalidated {count} cache entries")
        return count

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get Redis cache statistics"""
        try:
            client = self.get_redis_client()
            if not client:
                return {"status": "disconnected"}

            info = client.info()
            stats = {
                "status": "connected",
                "used_memory": info.get("used_memory_human", "Unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace": {},
            }

            # Count keys by pattern
            for pattern in ["entity:*", "community:*", "query:*", "retrieval:*"]:
                count = len(client.keys(pattern))
                stats["keyspace"][pattern] = count

            return stats

        except Exception as e:
            logger.warning(f"Could not get cache stats: {str(e)}")
            return {"status": "error", "message": str(e)}


# Singleton instance
cache_service = CacheService()
