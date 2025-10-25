# Terraform Infrastructure for AI Predictor Backend

This directory contains Terraform configuration for deploying a cost-optimized AWS infrastructure for the AI Predictor FastAPI backend.

## Architecture Overview

The infrastructure includes:

- **VPC with VPC Endpoints** (no NAT Gateway for cost savings)
  - S3 Gateway Endpoint (free)
  - ECR Interface Endpoints (API, Docker, CloudWatch Logs)
- **ECS Fargate Spot** (70% cost savings vs regular Fargate)
- **API Gateway HTTP API** (replaces ALB for cost savings)
- **S3 Buckets** for file storage and processed data
- **ECR Repository** for Docker images
- **IAM Roles** with least privilege access
- **CloudWatch Logs** for monitoring

## Cost Optimization

**Estimated Monthly Cost: ~$8-15**

- API Gateway HTTP API: $1-3
- VPC Interface Endpoints: $7-10
- ECS Fargate Spot: $4-6
- NAT Gateway: $0 (eliminated)
- S3 and CloudWatch: Minimal usage-based costs

**Savings vs Traditional Setup: ~$50-65/month (~80% reduction)**

## Prerequisites

1. AWS CLI configured with appropriate credentials
2. Terraform >= 1.5.0 installed
3. Docker image built and ready to push to ECR

## Quick Start

### 1. Configure Variables

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your specific values
```

### 2. Initialize Terraform

```bash
terraform init
```

### 3. Plan the Infrastructure

```bash
terraform plan
```

### 4. Apply the Infrastructure

```bash
terraform apply
```

### 5. Push Docker Image to ECR

After Terraform creates the infrastructure, get the ECR repository URL:

```bash
# Get ECR repository URL
export ECR_REPO=$(terraform output -raw ecr_repository_url)
export AWS_REGION=$(terraform output -json backend_environment_variables | jq -r .AWS_REGION)
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and tag the image
cd ../backend
docker build -t predictor-model-backend .
docker tag predictor-model-backend:latest $ECR_REPO:latest

# Push to ECR
docker push $ECR_REPO:latest
```

### 6. Update ECS Service

After pushing the image, update the ECS service to use the new task definition:

```bash
aws ecs update-service --cluster $(terraform output -raw ecs_cluster_name) \
  --service $(terraform output -raw ecs_service_name) \
  --force-new-deployment \
  --region $AWS_REGION
```

### 7. Get API Gateway URL

```bash
terraform output api_gateway_url
```

Use this URL to update your Amplify frontend configuration.

## Module Structure

- **networking/**: VPC, subnets, VPC endpoints
- **security/**: Security groups for ECS and API Gateway
- **s3/**: S3 buckets for files and data
- **ecr/**: ECR repository for Docker images
- **iam/**: IAM roles and policies
- **ecs/**: ECS cluster, task definitions, Fargate Spot service
- **api-gateway/**: API Gateway HTTP API with VPC Link

## Important Notes

### VPC Endpoints

- **S3 Gateway Endpoint**: Free, no hourly charges
- **Interface Endpoints**: ~$0.01/hour per endpoint per AZ
- Eliminates need for NAT Gateway ($0.045/hour + data transfer costs)

### Fargate Spot

- 70% cheaper than regular Fargate
- Tasks can be interrupted with 2-minute warning
- Suitable for stateless, fault-tolerant workloads
- Automatic fallback to regular Fargate if Spot capacity unavailable

### API Gateway HTTP API

- Lower cost than REST API (~$1 per million requests)
- Lower latency
- Built-in CORS support
- Integrated with VPC Link for private ECS access

## Outputs

After applying, Terraform provides important outputs:

- `api_gateway_url`: API endpoint URL
- `ecr_repository_url`: ECR repository for pushing images
- `s3_files_bucket_name`: S3 bucket for uploaded files
- `s3_data_bucket_name`: S3 bucket for processed data
- `ecs_cluster_name`: ECS cluster name
- `ecs_service_name`: ECS service name

## Terraform State Management

For production, configure remote state in S3:

1. Create S3 bucket for state:

   ```bash
   aws s3 mb s3://predictor-model-terraform-state
   aws s3api put-bucket-versioning --bucket predictor-model-terraform-state --versioning-configuration Status=Enabled
   ```

2. Create DynamoDB table for state locking:

   ```bash
   aws dynamodb create-table --table-name predictor-model-terraform-locks \
     --attribute-definitions AttributeName=LockID,AttributeType=S \
     --key-schema AttributeName=LockID,KeyType=HASH \
     --billing-mode PAY_PER_REQUEST
   ```

3. Uncomment backend configuration in `backend.tf`

4. Migrate state:

   ```bash
   terraform init -migrate-state
   ```

## Monitoring

- **CloudWatch Logs**: ECS task logs and API Gateway access logs
- **Container Insights**: Enabled on ECS cluster for metrics
- **ECS Service Auto-scaling**: Based on CPU (70%) and Memory (80%) utilization

## Cleanup

To destroy all infrastructure:

```bash
terraform destroy
```

**Note**: Ensure S3 buckets are empty before destroying (delete all objects).

## Troubleshooting

### ECS Tasks Not Starting

- Check CloudWatch logs: `/ecs/predictor-model-{env}-backend`
- Verify ECR image exists and is accessible
- Check VPC endpoint connectivity

### API Gateway Connection Issues

- Verify VPC Link status is AVAILABLE
- Check security group rules
- Ensure ECS service is running in private subnets

### S3 Access Issues

- Verify IAM task role has S3 permissions
- Check S3 Gateway Endpoint route table association
- Ensure bucket names are correctly configured in environment variables

## Support

For issues or questions, refer to the project documentation or contact the DevOps team.
