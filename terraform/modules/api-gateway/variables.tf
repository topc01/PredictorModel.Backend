variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for VPC Link"
  type        = list(string)
}

variable "api_gateway_sg_id" {
  description = "Security group ID for API Gateway VPC Link"
  type        = string
}

variable "service_discovery_arn" {
  description = "ARN of the service discovery service"
  type        = string
}

variable "cloud_map_namespace_name" {
  description = "Name of the Cloud Map namespace"
  type        = string
}

variable "ecs_service_name" {
  description = "Name of the ECS service"
  type        = string
}

variable "container_port" {
  description = "Port on which the container listens"
  type        = number
}

variable "cors_origins" {
  description = "List of allowed CORS origins"
  type        = list(string)
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

