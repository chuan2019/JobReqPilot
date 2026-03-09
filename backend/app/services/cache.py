"""Redis-backed cache for search results and embeddings."""

import hashlib
import json
import logging
import os

import redis.asyncio as redis

logger = logging.getLogger(__name__)

DEFAULT_TTL = 3600  # 1 hour


class CacheService:
    """Async Redis cache with JSON serialization and TTL."""

    def __init__(self, redis_url: str | None = None, ttl: int = DEFAULT_TTL):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.ttl = ttl
        self._redis: redis.Redis | None = None

    async def start(self) -> None:
        """Connect to Redis."""
        self._redis = redis.from_url(self.redis_url, decode_responses=True)
        try:
            await self._redis.ping()
            logger.info("Redis cache connected at %s", self.redis_url)
        except Exception as e:
            logger.warning("Redis not available (%s) — cache disabled", e)
            self._redis = None

    async def stop(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    @staticmethod
    def make_key(prefix: str, data: dict) -> str:
        """Generate a deterministic cache key from a dict."""
        serialized = json.dumps(data, sort_keys=True)
        digest = hashlib.sha256(serialized.encode()).hexdigest()[:16]
        return f"{prefix}:{digest}"

    async def get(self, key: str) -> dict | None:
        """Get a cached value. Returns None on miss or if cache is disabled."""
        if not self._redis:
            return None
        try:
            raw = await self._redis.get(key)
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.warning("Cache get failed for %s: %s", key, e)
        return None

    async def set(self, key: str, value: dict, ttl: int | None = None) -> None:
        """Store a value in cache with TTL."""
        if not self._redis:
            return
        try:
            raw = json.dumps(value)
            await self._redis.set(key, raw, ex=ttl or self.ttl)
        except Exception as e:
            logger.warning("Cache set failed for %s: %s", key, e)
