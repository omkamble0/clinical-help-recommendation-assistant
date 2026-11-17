"""
AegisMed - Cloud Cache & Rate Limiter API Routes
Endpoints for monitoring cache hits/misses, memory status, and administrative cache invalidation.
"""

from fastapi import APIRouter
from typing import Dict, Any

from app.core.cloud_cache import cloud_cache_service

router = APIRouter(prefix="/api/v1/cloud/cache", tags=["Cloud Cache & Performance"])


@router.get("/status", summary="Cloud Cache Telemetry & Hit-Ratio")
async def get_cache_status() -> Dict[str, Any]:
    """
    Returns real-time cache statistics:
    - Provider: Redis Cloud / AWS ElastiCache vs Local In-Memory LRU
    - Cache hits, misses, and hit-ratio percentage
    - Active cached queries count
    - Default TTL
    - Rate limiter policy
    """
    return cloud_cache_service.get_status()


@router.post("/clear", summary="Invalidate Cloud Cache")
async def clear_cache() -> Dict[str, str]:
    """
    Flushes all cached query responses and resets telemetry.
    Call this when updating medical database records or clinical guidelines.
    """
    cloud_cache_service.clear()
    return {"status": "success", "message": "Cloud cache successfully cleared"}
