variable "aws_region" {
  type        = string
  description = "AWS region for deployment (us-east-1 is recommended for full Free Tier compatibility)"
  default     = "us-east-1"
}

variable "project_name" {
  type        = string
  description = "Project identifier for naming resources"
  default     = "aegismed"
}

variable "environment" {
  type        = string
  description = "Deployment environment name"
  default     = "production"
}

variable "domain_name" {
  type        = string
  description = "Optional custom domain name (leave blank to use default cloudfront.net domain)"
  default     = ""
}
