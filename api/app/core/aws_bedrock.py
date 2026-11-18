"""
AegisMed - AWS Bedrock Generative AI & Titan Embeddings Engine
Directly integrates Amazon Bedrock runtime (Meta Llama 3 & Amazon Titan Embeddings v2)
for cloud-native, enterprise-grade clinical synthesis and vector embeddings via boto3.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional


class AWSBedrockService:
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.model_id = os.getenv("AWS_BEDROCK_MODEL", "meta.llama3-8b-instruct-v1:0")
        self.embed_model_id = os.getenv("AWS_BEDROCK_EMBED_MODEL", "amazon.titan-embed-text-v2:0")
        self._client = None
        self._is_connected = False
        self._init_bedrock()

    def _init_bedrock(self):
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        is_testing = os.getenv("TESTING") in ("true", "1") or "pytest" in os.sys.modules
        if is_testing and not access_key:
            self._is_connected = False
            return

        try:
            import boto3
            from botocore.config import Config

            cfg = Config(
                region_name=self.region,
                connect_timeout=3.0,
                read_timeout=10.0,
                retries={"max_attempts": 2}
            )

            if access_key and secret_key:
                self._client = boto3.client(
                    "bedrock-runtime",
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    config=cfg
                )
            else:
                self._client = boto3.client("bedrock-runtime", config=cfg)

            self._is_connected = True
        except Exception:
            self._is_connected = False
            self._client = None

    def generate(self, prompt: str, max_tokens: int = 400, temperature: float = 0.2) -> Optional[str]:
        """Invokes Meta Llama 3 on Amazon Bedrock."""
        if not self._is_connected or not self._client:
            return None

        try:
            body = json.dumps({
                "prompt": prompt,
                "max_gen_len": max_tokens,
                "temperature": temperature
            })
            response = self._client.invoke_model(
                modelId=self.model_id,
                body=body
            )
            response_body = json.loads(response["body"].read().decode("utf-8"))
            return response_body.get("generation", "").strip()
        except Exception as e:
            print(f"[!] Bedrock invoke warning: {e}")
            return None

    def embed(self, text: str, dimensions: int = 256) -> Optional[List[float]]:
        """Generates dense vector embedding using Amazon Titan Embeddings v2."""
        if not self._is_connected or not self._client:
            return None

        try:
            body = json.dumps({
                "inputText": text[:2048],
                "dimensions": dimensions,
                "normalize": True
            })
            response = self._client.invoke_model(
                modelId=self.embed_model_id,
                body=body
            )
            response_body = json.loads(response["body"].read().decode("utf-8"))
            return response_body.get("embedding")
        except Exception as e:
            print(f"[!] Bedrock Titan embedding warning: {e}")
            return None

    def get_status(self) -> Dict[str, Any]:
        """Returns AWS Bedrock telemetry and model metadata."""
        return {
            "service": "Amazon Bedrock (AWS Generative AI Engine)",
            "provider": "AWS Bedrock Runtime",
            "is_connected": self._is_connected,
            "region": self.region,
            "llm_foundation_model": self.model_id,
            "embeddings_foundation_model": self.embed_model_id,
            "architecture": "AWS Bedrock Managed Runtime via boto3",
            "compliance": "HIPAA-Eligible Foundation Model Service"
        }


# Global singleton instance
aws_bedrock_service = AWSBedrockService()
