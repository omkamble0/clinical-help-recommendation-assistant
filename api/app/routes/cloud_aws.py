"""
AegisMed - AWS Cloud Services API Routes
Endpoints for monitoring AWS S3 / SSM status and uploading clinical doctor consultation briefs.
"""

from fastapi import APIRouter
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.core.aws_storage import aws_storage_service
from app.core.aws_ssm import aws_ssm_service

router = APIRouter(prefix="/api/v1/cloud/aws", tags=["AWS Cloud Integration"])


class DoctorBriefRequest(BaseModel):
    query: str
    answer: str
    doctor_questions: List[str]
    citations: List[Any] = []


@router.get("/status", summary="AWS Cloud Infrastructure Status")
async def get_aws_status() -> Dict[str, Any]:
    """
    Returns real-time AWS Cloud status:
    - Amazon S3 storage connection, bucket, and encryption
    - AWS SSM Parameter Store status and free tier verification
    - HIPAA compliance standards
    """
    return {
        "storage": aws_storage_service.get_status(),
        "secrets_manager": aws_ssm_service.get_status(),
        "aws_architecture": {
            "cdn": "Amazon CloudFront (1 TB/mo Free Tier)",
            "storage": "Amazon S3 (5 GB Free Tier)",
            "secrets": "AWS SSM Parameter Store (100% Free)",
            "containers": "AWS ECR (500 MB Free) + App Runner / EC2 Free Tier",
            "estimated_monthly_bill": "$0.00 / month (Optimized for AWS Free Tier)"
        }
    }


@router.post("/brief", summary="Generate & Save Doctor Consultation Brief to AWS S3")
async def save_brief_to_s3(payload: DoctorBriefRequest) -> Dict[str, Any]:
    """
    Generates a structured, printable Doctor Consultation Brief and uploads it
    to Amazon S3 with AES-256 encryption (or local fallback storage).
    """
    return aws_storage_service.save_doctor_consultation_brief(
        query=payload.query,
        answer=payload.answer,
        doctor_questions=payload.doctor_questions,
        citations=payload.citations
    )
