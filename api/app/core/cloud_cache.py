"""
AegisMed - Cloud Caching & Rate Limiting Service
Provides sub-5ms semantic query caching and API abuse protection via Redis Cloud / AWS ElastiCache
with a thread-safe local in-memory LRU fallback.
"""

import os
import json
import time
import hashlib
from typing import Any, Optional, Dict, Tuple
from collections import OrderedDict
from threading import Lock

from app.config import settings


class LocalLRUCache:
    """Thread-safe in-memory LRU cache with TTL support for zero-dependency fallback."""
    def __init__(self, maxsize: int = 1000, default_ttl: int = 86400):
        self.maxsize = maxsize
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                return None
            val, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return val

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        duration = ttl if ttl is not None else self.default_ttl
        expiry = time.time() + duration
        with self._lock:
            if key in self._cache:
                del self._cache[key]
            elif len(self._cache) >= self.maxsize:
                self._cache.popitem(last=False)
            self._cache[key] = (value, expiry)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        with self._lock:
            now = time.time()
            return sum(1 for _, (_, exp) in self._cache.items() if exp > now)


class CloudCacheService:
    def __init__(self):
        self._redis = None
        self._is_redis = False
        self._redis_url = None
        self._lru = LocalLRUCache(maxsize=1000, default_ttl=getattr(settings, "CACHE_TTL_SECONDS", 86400))
        self._hits = 0
        self._misses = 0
        self._rate_limits: Dict[str, list] = {}
        self._rate_lock = Lock()
        self._init_connection()

    def _init_connection(self):
        redis_url = getattr(settings, "REDIS_URL", None) or os.getenv("REDIS_URL")
        if not getattr(settings, "is_offline", False) and redis_url and redis_url.strip():
            try:
                import redis
                clean_url = redis_url.strip()
                r = redis.from_url(clean_url, decode_responses=True, socket_timeout=1.5)
                r.ping()
                self._redis = r
                self._is_redis = True
                self._redis_url = clean_url
                print(f"[OK] Connected to Redis Cloud Cache at {clean_url.split('@')[-1]}")
                return
            except Exception as e:
                print(f"[*] Redis connection notice ({e}), using in-memory LRU cache.")

        self._redis = None
        self._is_redis = False

    def generate_key(self, prefix: str, text: str, **kwargs) -> str:
        """Creates a normalized, deterministic SHA-256 cache key."""
        normalized = " ".join(text.lower().strip().split())
        extras = sorted([f"{k}:{v}" for k, v in kwargs.items()])
        full_spec = f"{prefix}:{normalized}:{'|'.join(extras)}"
        h = hashlib.sha256(full_spec.encode("utf-8")).hexdigest()[:16]
        return f"aegismed:{prefix}:{h}"

    def get(self, key: str) -> Optional[Any]:
        """Retrieves a cached value from Redis Cloud or local LRU."""
        if self._is_redis and self._redis:
            try:
                raw = self._redis.get(key)
                if raw is not None:
                    self._hits += 1
                    return json.loads(raw)
            except Exception:
                pass

        val = self._lru.get(key)
        if val is not None:
            self._hits += 1
            return val

        self._misses += 1
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Stores a value in Redis Cloud or local LRU with TTL."""
        expiry = ttl if ttl is not None else getattr(settings, "CACHE_TTL_SECONDS", 86400)

        if self._is_redis and self._redis:
            try:
                self._redis.setex(key, expiry, json.dumps(value, default=str))
                return
            except Exception:
                pass

        self._lru.set(key, value, ttl=expiry)

    def check_rate_limit(self, client_id: str, max_requests: int = 60, window_seconds: int = 60) -> Tuple[bool, int, int]:
        """
        Sliding window rate limiter.
        Returns: (is_allowed, remaining_requests, reset_seconds)
        """
        now = time.time()
        key = f"aegismed:ratelimit:{client_id}"

        if self._is_redis and self._redis:
            try:
                pipe = self._redis.pipeline()
                pipe.zremrangebyscore(key, 0, now - window_seconds)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, window_seconds)
                _, _, count, _ = pipe.execute()
                remaining = max(0, max_requests - count)
                return (count <= max_requests, remaining, window_seconds)
            except Exception:
                pass

        # In-memory sliding window fallback
        with self._rate_lock:
            if client_id not in self._rate_limits:
                self._rate_limits[client_id] = []
            timestamps = [t for t in self._rate_limits[client_id] if now - t < window_seconds]
            timestamps.append(now)
            self._rate_limits[client_id] = timestamps
            count = len(timestamps)
            remaining = max(0, max_requests - count)
            return (count <= max_requests, remaining, window_seconds)

    def clear(self) -> None:
        """Flushes cache."""
        if self._is_redis and self._redis:
            try:
                self._redis.flushdb()
            except Exception:
                pass
        self._lru.clear()
        self._hits = 0
        self._misses = 0

    def get_status(self) -> Dict[str, Any]:
        """Returns cache telemetry, hit-ratio, provider, and memory metrics."""
        total = self._hits + self._misses
        hit_ratio = round((self._hits / total) * 100, 1) if total > 0 else 0.0
        active_keys = 0

        if self._is_redis and self._redis:
            try:
                active_keys = self._redis.dbsize()
            except Exception:
                pass
        else:
            active_keys = self._lru.size()

        return {
            "service": "AegisMed Cloud Cache & Rate Limiter",
            "provider": "Redis Cloud / ElastiCache" if self._is_cloud_cache else "Local In-Memory LRU Cache",
            "is_redis_managed": self._is_cloud_cache,
            "connection_status": "connected",
            "active_cached_keys": active_keys,
            "cache_hits": self._hits,
            "cache_misses": self._misses,
            "hit_ratio_pct": hit_ratio,
            "default_ttl_seconds": getattr(settings, "CACHE_TTL_SECONDS", 86400),
            "rate_limiter_policy": "Sliding Window (60 req/min/client)"
        }

    @property
    def _is_cloud_cache(self) -> bool:
        return self._is_redis and self._redis is not None


# Global singleton instance
cloud_cache_service = CloudCacheService()
