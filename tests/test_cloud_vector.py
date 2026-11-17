"""
Unit tests for AegisMed Cloud Vector Database service & endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.cloud_vector import text_to_dense_vector, mask_url, cloud_vector_service

client = TestClient(app)


def test_text_to_dense_vector():
    vec = text_to_dense_vector("type 2 diabetes metformin", dim=128)
    assert len(vec) == 128
    # Ensure vector is normalized (magnitude approx 1.0)
    norm = sum(x * x for x in vec) ** 0.5
    assert abs(norm - 1.0) < 1e-4


def test_mask_url():
    assert mask_url(None) is None
    masked = mask_url("https://abcdef12345.us-east4-0.gcp.cloud.qdrant.io:6333")
    assert "abcdef12345" not in masked
    assert "cloud.qdrant.io:6333" in masked


def test_cloud_vector_status_endpoint():
    response = client.get("/api/v1/cloud/vector/status")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert "provider" in data
    assert "latency_ms" in data
    assert data["vector_dimension"] == 128
    assert data["distance_metric"] == "Cosine"
    assert data["architecture"] == "HNSW (Hierarchical Navigable Small World)"


def test_cloud_vector_search_endpoint():
    response = client.get("/api/v1/cloud/vector/search?q=hypertension+blood+pressure&limit=3")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_cloud_vector_search_empty_query():
    response = client.get("/api/v1/cloud/vector/search?q=")
    assert response.status_code == 400
