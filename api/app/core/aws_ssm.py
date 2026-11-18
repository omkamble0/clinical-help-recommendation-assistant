"""
AegisMed - AWS SSM Parameter Store Secret Management
Loads secure production parameters (API keys, connection strings) from AWS Systems Manager (SSM)
Parameter Store. Standard SSM parameters are 100% permanently free on AWS (saving $0.40/secret/mo).
"""

import os
from typing import Dict, Any, Optional


class AWSSSMService:
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.parameter_prefix = os.getenv("AWS_SSM_PREFIX", "/aegismed/production/")
        self._ssm_client = None
        self._is_connected = False
        self._init_ssm()

    def _init_ssm(self):
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
                connect_timeout=2.0,
                read_timeout=2.0,
                retries={"max_attempts": 2}
            )

            if access_key and secret_key:
                self._ssm_client = boto3.client(
                    "ssm",
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    config=cfg
                )
            else:
                self._ssm_client = boto3.client("ssm", config=cfg)

            self._is_connected = True
        except Exception:
            self._is_connected = False
            self._ssm_client = None

    def get_parameter(self, param_name: str, default: Optional[str] = None) -> Optional[str]:
        """Fetches decrypted parameter from AWS SSM or returns default/env variable."""
        full_path = f"{self.parameter_prefix.rstrip('/')}/{param_name.lstrip('/')}"

        if self._is_connected and self._ssm_client:
            try:
                resp = self._ssm_client.get_parameter(Name=full_path, WithDecryption=True)
                val = resp.get("Parameter", {}).get("Value")
                if val:
                    return val
            except Exception:
                pass

        return os.getenv(param_name, default)

    def get_status(self) -> Dict[str, Any]:
        """Returns AWS SSM configuration and service status."""
        return {
            "service": "AWS Systems Manager (SSM) Parameter Store",
            "provider": "AWS Systems Manager Standard Tier",
            "is_connected": self._is_connected,
            "region": self.region,
            "parameter_namespace": self.parameter_prefix,
            "security_type": "SecureString (KMS Encrypted)",
            "tier": "Standard Secure Parameter Storage"
        }


# Global singleton instance
aws_ssm_service = AWSSSMService()
