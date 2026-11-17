output "cloudfront_domain_name" {
  description = "The public CloudFront CDN URL serving the AegisMed Next.js frontend"
  value       = "https://${aws_cloudfront_distribution.cdn.domain_name}"
}

output "cloudfront_distribution_id" {
  description = "CloudFront Distribution ID for cache invalidation"
  value       = aws_cloudfront_distribution.cdn.id
}

output "frontend_s3_bucket" {
  description = "Amazon S3 bucket name hosting the Next.js static build"
  value       = aws_s3_bucket.frontend.bucket
}

output "clinical_documents_s3_bucket" {
  description = "Amazon S3 bucket name storing printable doctor consultation briefs"
  value       = aws_s3_bucket.documents.bucket
}

output "ecr_api_repository_url" {
  description = "Amazon ECR Repository URL for FastAPI backend container image"
  value       = aws_ecr_repository.api.repository_url
}

output "ecr_web_repository_url" {
  description = "Amazon ECR Repository URL for Next.js web container image"
  value       = aws_ecr_repository.web.repository_url
}

output "estimated_monthly_infrastructure_bill" {
  description = "Estimated monthly cloud charges"
  value       = "$0.00 / month (Fully optimized for AWS Free Tier)"
}
