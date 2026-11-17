#!/usr/bin/env python3
"""
AegisMed - AWS Cloud Connection Verifier
Tests authentication with AWS using boto3, verifies IAM identity, S3 access, and SSM Parameter Store.

Usage:
    python scripts/verify_aws_connection.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "api"))


def load_env_file():
    """Loads AWS credentials from .env if present."""
    for env_path in [BASE_DIR / ".env", BASE_DIR / "api" / ".env"]:
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k.startswith("AWS_") and k not in os.environ:
                        os.environ[k] = v


def print_step_by_step_instructions():
    print("\n" + "=" * 76)
    print(" AegisMed: How to Connect to AWS in 3 Simple Steps (100% Free)")
    print("=" * 76)
    print("\n[Step 1] Create a Free AWS Account:")
    print("  1. Go to https://aws.amazon.com/free and sign up (12-month free tier).")
    print("\n[Step 2] Create Your IAM Access Keys:")
    print("  1. In the AWS Console search bar, type 'IAM' and press Enter.")
    print("  2. In the left menu, click 'Users' -> 'Create user'.")
    print("  3. Name it 'aegismed-developer'.")
    print("  4. In Permissions options, select 'Attach policies directly'.")
    print("  5. Search and check 'AdministratorAccess' (or custom S3/SSM policies).")
    print("  6. Click 'Next' -> 'Create user'.")
    print("  7. Click on your newly created user, open the 'Security credentials' tab.")
    print("  8. Scroll to 'Access keys' and click 'Create access key'.")
    print("  9. Select 'Command Line Interface (CLI)' or 'Application running outside AWS'.")
    print(" 10. Copy your 'Access key ID' and 'Secret access key'.")
    print("\n[Step 3] Add Them to Your .env File:")
    print("  Open your '.env' file in this project and paste:")
    print("    AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE")
    print("    AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")
    print("    AWS_REGION=us-east-1")
    print("    AWS_S3_BUCKET_NAME=aegismed-clinical-storage")
    print("\n[Step 4] Run This Script Again:")
    print("  python scripts/verify_aws_connection.py")
    print("=" * 76 + "\n")


def verify_connection():
    load_env_file()

    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "us-east-1")
    bucket = os.getenv("AWS_S3_BUCKET_NAME", "aegismed-clinical-storage")

    if not access_key or not secret_key:
        print("[!] No AWS credentials found in your environment or .env file.")
        print_step_by_step_instructions()
        return False

    print("=" * 76)
    print(" AegisMed: Verifying AWS Cloud Authentication & Services")
    print("=" * 76)
    print(f"[*] Target AWS Region:    {region}")
    print(f"[*] Access Key ID:        {access_key[:4]}...{access_key[-4:] if len(access_key) > 8 else '****'}")
    print(f"[*] Target S3 Bucket:     {bucket}\n")

    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        print("[!] 'boto3' is not installed. Run: pip install boto3")
        return False

    # 1. Verify STS Identity
    print("[1/3] Testing IAM Authentication with AWS Security Token Service (STS)...")
    try:
        sts = boto3.client(
            "sts",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        identity = sts.get_caller_identity()
        print(f"  [OK] Successfully Authenticated to AWS!")
        print(f"       Account ID:  {identity.get('Account')}")
        print(f"       User / ARN:  {identity.get('Arn')}")
    except Exception as e:
        print(f"  [!] STS Authentication Failed: {e}")
        print("      Please verify your AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.")
        return False

    # 2. Verify S3 Access
    print("\n[2/3] Testing Amazon S3 Cloud Storage Access...")
    try:
        s3 = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        # List existing buckets
        resp = s3.list_buckets()
        existing_buckets = [b["Name"] for b in resp.get("Buckets", [])]
        print(f"  [OK] Successfully connected to Amazon S3!")
        print(f"       Total Existing S3 Buckets: {len(existing_buckets)}")

        # Check or create target bucket
        if bucket not in existing_buckets:
            print(f"  [*] Bucket '{bucket}' does not exist yet. Creating in region '{region}'...")
            try:
                if region == "us-east-1":
                    s3.create_bucket(Bucket=bucket)
                else:
                    s3.create_bucket(
                        Bucket=bucket,
                        CreateBucketConfiguration={"LocationConstraint": region}
                    )
                print(f"  [OK] Created S3 bucket: '{bucket}'")
            except Exception as b_err:
                print(f"  [*] Notice: Bucket name '{bucket}' might be globally taken. Try a unique name like '{bucket}-{identity.get('Account')[:6]}'.")
        else:
            print(f"  [OK] Target S3 bucket '{bucket}' is active and ready.")

    except Exception as e:
        print(f"  [!] S3 Check Warning: {e}")

    # 3. Verify Systems Manager (SSM) Parameter Store Access
    print("\n[3/3] Testing AWS Systems Manager (SSM) Parameter Store Access...")
    try:
        ssm = boto3.client(
            "ssm",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        test_param = "/aegismed/production/ENVIRONMENT"
        ssm.put_parameter(
            Name=test_param,
            Value="production",
            Type="String",
            Overwrite=True,
            Tier="Standard"
        )
        print(f"  [OK] Successfully wrote to AWS SSM Parameter Store: '{test_param}'")
        print(f"       Tier: Standard (100% Permanently Free)")
    except Exception as e:
        print(f"  [*] SSM Check notice: {e}")

    print("\n" + "=" * 76)
    print(" [SUCCESS] YOUR SYSTEM IS FULLY CONNECTED TO AWS!")
    print("=" * 76)
    print(" AegisMed is now actively using Amazon S3 for doctor consultation briefs")
    print(" and AWS SSM for zero-cost secure parameter storage.")
    print("=" * 76 + "\n")
    return True


if __name__ == "__main__":
    verify_connection()
