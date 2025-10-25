output "files_bucket_name" {
  description = "Name of the S3 bucket for uploaded files"
  value       = aws_s3_bucket.files.id
}

output "files_bucket_arn" {
  description = "ARN of the S3 bucket for uploaded files"
  value       = aws_s3_bucket.files.arn
}

output "data_bucket_name" {
  description = "Name of the S3 bucket for processed data"
  value       = aws_s3_bucket.data.id
}

output "data_bucket_arn" {
  description = "ARN of the S3 bucket for processed data"
  value       = aws_s3_bucket.data.arn
}

