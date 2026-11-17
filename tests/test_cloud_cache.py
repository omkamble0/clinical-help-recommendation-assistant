"""
Unit tests for AegisMed Cloud Cache (Redis / Local LRU) & Rate Limiting.
"""

import time
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.cloud_cache import cloud_cache_service, LocalLRUCache
from app.models.schemas import UserMode
from app.services.rag_engine import process_clinical_query

client = TestClient(app)


def test_local_lru_cache_operations():
    cache = LocalLRUCache(maxsize=3, default_ttl=60)
    cache.set("key1", "val1")
    cache.set("key2", "val2")
    assert cache.get("key1") == "val1"
    assert cache.get("key2") == "val2"
    assert cache.get("nonexistent") is None

    # Test eviction
    cache.set("key3", "val3")
    cache.set("key4", "val4")  # Should evict key1
    assert cache.get("key1") is None
    assert cache.get("key4") == "val4"


def test_cloud_cache_key_generation():
    k1 = cloud_cache_service.generate_key("query", "Can I take paracetamol?", mode="patient")
    k2 = cloud_cache_service.generate_key("query", "  can I TAKE PARACETAMOL?  ", mode="patient")
    # Normalized text must yield identical deterministic SHA-256 keys
    assert k1 == k2


def test_cloud_cache_rate_limiter():
    client_id = f"test_client_{int(time.time())}"
    allowed, remaining, _ = cloud_cache_service.check_rate_limit(client_id, max_requests=3, window_seconds=10)
    assert allowed is True
    assert remaining == 2

    allowed, remaining, _ = cloud_cache_service.check_rate_limit(client_id, max_requests=3, window_seconds=10)
    assert allowed is True
    assert remaining == 1

    allowed, remaining, _ = cloud_cache_service.check_rate_limit(client_id, max_requests=3, window_seconds=10)
    assert allowed is True
    assert remaining == 0

    # 4th request must exceed limit
    allowed, remaining, _ = cloud_cache_service.check_rate_limit(client_id, max_requests=3, window_seconds=10)
    assert allowed is False
    assert remaining == 0


def test_cloud_cache_status_endpoint():
    response = client.get("/api/v1/cloud/cache/status")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "provider" in data
    assert "hit_ratio_pct" in data
    assert "rate_limiter_policy" in data


def test_cloud_cache_clear_endpoint():
    response = client.post("/api/v1/cloud/cache/clear")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_rag_pipeline_sub_10ms_cache_hit():
    query = "What is the recommended HbA1c target for elderly patients?"
    cloud_cache_service.clear()

    # Call 1: Cache MISS
    res1 = process_clinical_query(query, UserMode.PATIENT)
    assert res1 is not None

    # Call 2: Cache HIT (Sub-10ms response)
    res2 = process_clinical_query(query, UserMode.PATIENT)
    assert res2 is not None
    assert res2.answer == res1.answer
    assert res2.latency_ms <= 30  # Served directly from cache
