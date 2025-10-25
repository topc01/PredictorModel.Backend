output "vpc_id" {
  description = "ID of the VPC"
  value       = module.networking.vpc_id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = module.networking.private_subnet_ids
}

output "public_subnet_ids" {
  description = "IDs of public subnets"
  value       = module.networking.public_subnet_ids
}

output "s3_files_bucket_name" {
  description = "Name of the S3 bucket for uploaded files"
  value       = module.s3.files_bucket_name
}

output "s3_data_bucket_name" {
  description = "Name of the S3 bucket for processed data"
  value       = module.s3.data_bucket_name
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = module.ecr.repository_url
}

output "ecr_repository_name" {
  description = "Name of the ECR repository"
  value       = module.ecr.repository_name
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = module.ecs.service_name
}

output "api_gateway_url" {
  description = "URL of the API Gateway endpoint"
  value       = module.api_gateway.api_gateway_url
}

output "api_gateway_id" {
  description = "ID of the API Gateway"
  value       = module.api_gateway.api_gateway_id
}

output "cloud_map_namespace" {
  description = "Cloud Map namespace for service discovery"
  value       = module.ecs.cloud_map_namespace_name
}

# Environment variables for backend application
output "backend_environment_variables" {
  description = "Environment variables to configure in the backend application"
  value = {
    AWS_REGION        = var.aws_region
    S3_FILES_BUCKET   = module.s3.files_bucket_name
    S3_DATA_BUCKET    = module.s3.data_bucket_name
    API_GATEWAY_URL   = module.api_gateway.api_gateway_url
  }
}

