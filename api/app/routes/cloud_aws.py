"""
AegisMed - AWS Cloud Services API Routes
Endpoints for monitoring AWS S3 / SSM status and uploading clinical doctor consultation briefs.
"""

from fastapi import APIRouter
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

from app.core.aws_storage import aws_storage_service
from app.core.aws_ssm import aws_ssm_service
from app.core.aws_bedrock import aws_bedrock_service

router = APIRouter(prefix="/api/v1/cloud/aws", tags=["AWS Cloud Integration"])


class DoctorBriefRequest(BaseModel):
    query: str
    answer: str
    doctor_questions: List[str]
    citations: List[Any] = []


class BedrockPromptRequest(BaseModel):
    prompt: str
    max_tokens: int = 300


@router.get("/status", summary="AWS Cloud Infrastructure Status")
async def get_aws_status() -> Dict[str, Any]:
    """
    Returns real-time AWS Cloud status:
    - Amazon Bedrock Foundation Models (Meta Llama 3 & Amazon Titan Embeddings)
    - Amazon S3 storage connection, bucket, and encryption
    - AWS SSM Parameter Store status and encrypted secrets management
    - HIPAA compliance standards
    """
    return {
        "bedrock_ai": aws_bedrock_service.get_status(),
        "storage": aws_storage_service.get_status(),
        "secrets_manager": aws_ssm_service.get_status(),
        "aws_architecture": {
            "generative_ai": "Amazon Bedrock (Meta Llama 3 8B)",
            "embeddings": "Amazon Titan Embeddings v2 (Dense 256-dim)",
            "cdn": "Amazon CloudFront Global CDN",
            "storage": "Amazon S3 (AES-256 Server-Side Encryption)",
            "secrets": "AWS SSM Parameter Store (Secure String KMS)",
            "containers": "AWS ECR & Microservices Orchestration",
            "compliance": "HIPAA-Aligned Server-Side Encryption"
        }
    }


@router.post("/bedrock/generate", summary="Generate Clinical Response via Amazon Bedrock")
async def generate_bedrock(payload: BedrockPromptRequest) -> Dict[str, Any]:
    """
    Directly invokes Meta Llama 3 on Amazon Bedrock runtime.
    """
    out = aws_bedrock_service.generate(payload.prompt, max_tokens=payload.max_tokens)
    return {
        "provider": "Amazon Bedrock (AWS)",
        "model": "meta.llama3-8b-instruct-v1:0",
        "output": out or "Model generation offline or pending IAM activation"
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
