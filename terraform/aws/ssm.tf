# ==============================================================================
# AWS Systems Manager (SSM) Parameter Store
# Standard tier parameters are 100% permanently free on AWS
# ==============================================================================

resource "aws_ssm_parameter" "environment" {
  name        = "/${var.project_name}/${var.environment}/ENVIRONMENT"
  description = "Application deployment environment"
  type        = "String"
  value       = var.environment
  tier        = "Standard"
}

resource "aws_ssm_parameter" "triage_enabled" {
  name        = "/${var.project_name}/${var.environment}/EMERGENCY_TRIAGE_ENABLED"
  description = "Enable deterministic emergency safety triage"
  type        = "String"
  value       = "true"
  tier        = "Standard"
}

resource "aws_ssm_parameter" "qdrant_collection" {
  name        = "/${var.project_name}/${var.environment}/QDRANT_COLLECTION"
  description = "Active vector collection name"
  type        = "String"
  value       = "medical_knowledge_collection"
  tier        = "Standard"
}

resource "aws_ssm_parameter" "s3_bucket" {
  name        = "/${var.project_name}/${var.environment}/AWS_S3_BUCKET_NAME"
  description = "Target S3 bucket for clinical doctor briefs"
  type        = "String"
  value       = aws_s3_bucket.documents.bucket
  tier        = "Standard"
}

resource "aws_ssm_parameter" "openai_api_key_placeholder" {
  name        = "/${var.project_name}/${var.environment}/OPENAI_API_KEY"
  description = "OpenAI API Key (Set via AWS Console or CLI)"
  type        = "SecureString"
  value       = "placeholder_set_in_aws_console"
  tier        = "Standard"

  lifecycle {
    ignore_changes = [value]
  }
}
