"""
AegisMed - Cloud Vector Database API Routes
Endpoints for monitoring, querying, and synchronizing with Qdrant Cloud or local vector engines.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.core.cloud_vector import cloud_vector_service

router = APIRouter(prefix="/api/v1/cloud/vector", tags=["Cloud Vector Database"])


class CloudVectorSearchResult(BaseModel):
    id: Any
    score: float
    name: str
    icd10: str
    specialty: str
    organ_system: str
    patient_summary: str
    symptoms_count: int
    solutions_count: int


@router.get("/status", summary="Cloud Vector Database Health & Metrics")
async def get_vector_status() -> Dict[str, Any]:
    """
    Returns real-time health, cluster latency, vector dimension,
    and index status for Qdrant Cloud or local vector storage.
    """
    return cloud_vector_service.get_status()


@router.get("/search", response_model=List[CloudVectorSearchResult], summary="Dense Semantic Vector Search")
async def search_vectors(
    q: str = Query(..., description="Clinical question, symptom description, or disease name"),
    limit: int = Query(5, ge=1, le=25, description="Number of nearest vector matches to return")
):
    """
    Performs cosine similarity search against the vector database (Qdrant Cloud or embedded)
    returning the top-k nearest clinical condition vectors with metadata.
    """
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query string 'q' cannot be empty")
    return cloud_vector_service.search(query=q.strip(), limit=limit)
