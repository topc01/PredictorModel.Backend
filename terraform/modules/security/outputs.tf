output "ecs_security_group_id" {
  description = "Security group ID for ECS tasks"
  value       = aws_security_group.ecs_tasks.id
}

output "api_gateway_sg_id" {
  description = "Security group ID for API Gateway VPC Link"
  value       = aws_security_group.api_gateway.id
}

