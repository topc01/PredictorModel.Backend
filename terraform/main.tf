terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = merge(
      var.tags,
      {
        Environment = var.environment
      }
    )
  }
}

# Locals for common resource naming
locals {
  name_prefix = "${var.project_name}-${var.environment}"
  
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
      Project     = var.project_name
    }
  )
}

# Networking Module
module "networking" {
  source = "./modules/networking"

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones
  
  tags = local.common_tags
}

# Security Groups Module
module "security" {
  source = "./modules/security"

  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.networking.vpc_id
  vpc_cidr     = var.vpc_cidr
  
  tags = local.common_tags
}

# S3 Module
module "s3" {
  source = "./modules/s3"

  project_name = var.project_name
  environment  = var.environment
  cors_origins = var.cors_origins
  
  tags = local.common_tags
}

# ECR Module
module "ecr" {
  source = "./modules/ecr"

  project_name = var.project_name
  environment  = var.environment
  
  tags = local.common_tags
}

# IAM Module
module "iam" {
  source = "./modules/iam"

  project_name       = var.project_name
  environment        = var.environment
  aws_region         = var.aws_region
  s3_files_bucket_arn = module.s3.files_bucket_arn
  s3_data_bucket_arn  = module.s3.data_bucket_arn
  ecr_repository_arn  = module.ecr.repository_arn
  
  tags = local.common_tags
}

# ECS Module
module "ecs" {
  source = "./modules/ecs"

  project_name            = var.project_name
  environment             = var.environment
  aws_region              = var.aws_region
  vpc_id                  = module.networking.vpc_id
  private_subnet_ids      = module.networking.private_subnet_ids
  ecs_security_group_id   = module.security.ecs_security_group_id
  
  ecr_repository_url      = module.ecr.repository_url
  container_port          = var.container_port
  container_cpu           = var.container_cpu
  container_memory        = var.container_memory
  
  task_execution_role_arn = module.iam.ecs_task_execution_role_arn
  task_role_arn           = module.iam.ecs_task_role_arn
  
  s3_files_bucket_name    = module.s3.files_bucket_name
  s3_data_bucket_name     = module.s3.data_bucket_name
  
  desired_count           = var.desired_count
  min_capacity            = var.min_capacity
  max_capacity            = var.max_capacity
  
  tags = local.common_tags
}

# API Gateway Module
module "api_gateway" {
  source = "./modules/api-gateway"

  project_name              = var.project_name
  environment               = var.environment
  vpc_id                    = module.networking.vpc_id
  private_subnet_ids        = module.networking.private_subnet_ids
  api_gateway_sg_id         = module.security.api_gateway_sg_id
  
  service_discovery_arn     = module.ecs.service_discovery_arn
  cloud_map_namespace_name  = module.ecs.cloud_map_namespace_name
  ecs_service_name          = module.ecs.service_name
  container_port            = var.container_port
  
  cors_origins              = var.cors_origins
  
  tags = local.common_tags
}

