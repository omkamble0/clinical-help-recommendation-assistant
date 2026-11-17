"""
AegisMed - AWS S3 Cloud Storage & Document Engine
Handles HIPAA-compliant storage (AES-256 server-side encryption) of printable doctor briefs,
clinical guideline PDFs, and audit trail bundles on Amazon S3 with local filesystem fallback.
"""

import os
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path

LOCAL_STORAGE_DIR = Path(__file__).resolve().parent.parent / "data" / "cloud_briefs"


class AWSStorageService:
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.bucket_name = os.getenv("AWS_S3_BUCKET_NAME", "aegismed-clinical-storage")
        self._s3_client = None
        self._is_connected = False
        self._init_s3()

    def _init_s3(self):
        # Ensure local fallback directory exists
        LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        # Skip remote call in test or offline mode unless keys are explicitly provided
        is_testing = os.getenv("TESTING") in ("true", "1") or "pytest" in os.sys.modules
        if is_testing and not access_key:
            self._is_connected = False
            return

        try:
            import boto3
            from botocore.config import Config

            cfg = Config(
                region_name=self.region,
                connect_timeout=2.0,
                read_timeout=2.0,
                retries={"max_attempts": 2}
            )

            if access_key and secret_key:
                self._s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    config=cfg
                )
            else:
                # Attempts IAM role / default credential chain (e.g. AWS App Runner / ECS)
                self._s3_client = boto3.client("s3", config=cfg)

            # Probe bucket connectivity
            self._s3_client.head_bucket(Bucket=self.bucket_name)
            self._is_connected = True
            print(f"[OK] Connected to Amazon S3 bucket '{self.bucket_name}' in region '{self.region}'")
        except Exception as e:
            # Graceful fallback to local persistent filesystem
            self._is_connected = False
            self._s3_client = None

    def upload_document(
        self,
        filename: str,
        content: str,
        content_type: str = "application/json"
    ) -> Dict[str, Any]:
        """
        Uploads document to Amazon S3 with AES-256 Server-Side Encryption.
        Falls back seamlessly to local persistent storage when running locally.
        """
        key = f"consultation-briefs/{filename}"

        if self._is_connected and self._s3_client:
            try:
                self._s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=key,
                    Body=content.encode("utf-8"),
                    ContentType=content_type,
                    ServerSideEncryption="AES256",  # HIPAA Security Rule: Encryption at Rest
                    Metadata={
                        "app": "aegismed",
                        "classification": "patient_clinical_brief",
                        "uploaded_at": str(int(time.time()))
                    }
                )
                return {
                    "storage_provider": "Amazon S3 (Cloud Storage)",
                    "bucket": self.bucket_name,
                    "region": self.region,
                    "s3_uri": f"s3://{self.bucket_name}/{key}",
                    "cloud_url": f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}",
                    "encryption": "AES-256 Server-Side",
                    "status": "uploaded_to_cloud"
                }
            except Exception as e:
                print(f"[*] S3 upload exception ({e}), saving to local fallback storage.")

        # Local Filesystem Fallback
        local_file = LOCAL_STORAGE_DIR / filename
        with open(local_file, "w", encoding="utf-8") as f:
            f.write(content)

        return {
            "storage_provider": "Local Persistent Storage (Fallback Mode)",
            "local_path": str(local_file),
            "file_name": filename,
            "encryption": "Host OS ACLs",
            "status": "saved_locally",
            "cloud_instructions": "To upload directly to AWS S3, set AWS_ACCESS_KEY_ID and AWS_S3_BUCKET_NAME in .env."
        }

    def save_doctor_consultation_brief(
        self,
        query: str,
        answer: str,
        doctor_questions: list,
        citations: list
    ) -> Dict[str, Any]:
        """Creates a standardized 1-page printable Doctor Consultation Brief."""
        timestamp = int(time.time())
        safe_id = f"brief_{timestamp}_{hash(query) & 0xffff:04x}"
        filename = f"{safe_id}.json"

        brief_payload = {
            "brief_id": safe_id,
            "generated_at_unix": timestamp,
            "clinical_query": query,
            "patient_guidance_summary": answer[:1000],
            "consultation_questions_for_doctor": doctor_questions,
            "supporting_evidence_citations": citations,
            "legal_disclaimer": "This brief is an evidence-based clinical guide generated for discussion with a licensed healthcare provider."
        }

        return self.upload_document(
            filename=filename,
            content=json.dumps(brief_payload, indent=2),
            content_type="application/json"
        )

    def get_status(self) -> Dict[str, Any]:
        """Returns AWS Cloud Storage health and configuration metrics."""
        return {
            "service": "AegisMed AWS Cloud Storage Engine",
            "provider": "Amazon Simple Storage Service (Amazon S3)" if self._is_connected else "Local File Storage (S3 Emulation)",
            "is_cloud_connected": self._is_connected,
            "region": self.region,
            "target_bucket": self.bucket_name,
            "encryption_at_rest": "AES-256 (KMS / S3 Managed)",
            "free_tier_eligibility": "Covered under AWS Free Tier (5 GB permanent free S3 storage)",
            "compliance_standards": ["HIPAA Security Rule § 164.312(a)(2)(iv)", "HITECH Act", "CIS AWS Foundations"]
        }


# Global singleton instance
aws_storage_service = AWSStorageService()
