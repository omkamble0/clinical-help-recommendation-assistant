"""
Unit tests for AegisMed AWS Cloud (S3, SSM & Doctor Consultation Brief) services.
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.aws_storage import aws_storage_service, LOCAL_STORAGE_DIR
from app.core.aws_ssm import aws_ssm_service

client = TestClient(app)


def test_aws_storage_status_endpoint():
    response = client.get("/api/v1/cloud/aws/status")
    assert response.status_code == 200
    data = response.json()
    assert "storage" in data
    assert "secrets_manager" in data
    assert "aws_architecture" in data
    assert "Amazon CloudFront" in data["aws_architecture"]["cdn"]
    assert "Amazon S3" in data["aws_architecture"]["storage"]
    assert "AWS SSM Parameter Store" in data["aws_architecture"]["secrets"]


def test_aws_save_brief_endpoint():
    payload = {
        "query": "Is metformin safe with mild renal impairment?",
        "answer": "Metformin can be used with eGFR between 45-59 ml/min at a reduced dose with close renal monitoring.",
        "doctor_questions": [
            "What is my current eGFR number?",
            "Do I need to check my kidney blood test every 3 or 6 months?"
        ],
        "citations": [1, 2]
    }
    response = client.post("/api/v1/cloud/aws/brief", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("uploaded_to_cloud", "saved_locally")
    assert "storage_provider" in data


def test_aws_storage_local_fallback_write():
    filename = "test_clinical_brief_unit_test.json"
    content = json.dumps({"test": "data", "app": "aegismed"})
    res = aws_storage_service.upload_document(filename, content)
    assert res["status"] in ("uploaded_to_cloud", "saved_locally")

    # If in local fallback mode, verify file was written on disk
    if res["status"] == "saved_locally":
        target = LOCAL_STORAGE_DIR / filename
        assert target.exists()
        target.unlink()  # Clean up test artifact


def test_aws_ssm_service_status():
    status = aws_ssm_service.get_status()
    assert "service" in status
    assert "Systems Manager" in status["service"]
    assert "Standard" in status["provider"]


def test_aws_bedrock_service_status():
    from app.core.aws_bedrock import aws_bedrock_service
    status = aws_bedrock_service.get_status()
    assert "service" in status
    assert "Amazon Bedrock" in status["service"]
    assert "meta.llama3-8b-instruct-v1:0" in status["llm_foundation_model"]


def test_aws_bedrock_generate_endpoint():
    response = client.post("/api/v1/cloud/aws/bedrock/generate", json={"prompt": "Ping", "max_tokens": 10})
    assert response.status_code == 200
    data = response.json()
    assert "provider" in data
    assert "Amazon Bedrock" in data["provider"]
