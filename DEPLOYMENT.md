# Deployment Guide - AI Predictor Backend

This guide walks you through deploying the AI Predictor backend to AWS using the cost-optimized Terraform infrastructure.

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Terraform** >= 1.5.0 installed
4. **Docker** installed for building images
5. **Git** for version control

## Architecture Overview

The deployment uses:

- **ECS Fargate Spot** for running containers (70% cost savings)
- **API Gateway HTTP API** instead of ALB (80% cost savings)
- **VPC Endpoints** instead of NAT Gateway (eliminates $32-45/month)
- **S3** for file and data storage
- **ECR** for Docker images

**Total estimated cost: $8-15/month** (vs $60-80 traditional setup)

## Step-by-Step Deployment

### Step 1: Clone and Prepare Repository

```bash
cd /Users/topc/Projects/AI-Predictor/PredictorModel.Backend
```

### Step 2: Configure Terraform Variables

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and adjust values:

```hcl
project_name = "predictor-model"
environment  = "prod"  # or "dev", "staging"
aws_region   = "us-east-1"

container_cpu    = 512   # 0.5 vCPU
container_memory = 1024  # 1 GB

cors_origins = [
  "https://main.d12abg5dtejald.amplifyapp.com",
  "https://develop.d12abg5dtejald.amplifyapp.com"
]
```

### Step 3: Initialize and Apply Terraform

```bash
# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Apply the infrastructure
terraform apply
```

Type `yes` when prompted to create the infrastructure.

**This will take 5-10 minutes** to create:

- VPC with subnets and VPC endpoints
- Security groups
- S3 buckets
- ECR repository
- IAM roles
- ECS cluster
- API Gateway

### Step 4: Get Infrastructure Outputs

After Terraform completes, capture the outputs:

```bash
# Save outputs to file
terraform output -json > outputs.json

# Get specific values
export ECR_REPO=$(terraform output -raw ecr_repository_url)
export AWS_REGION=$(terraform output -raw aws_region || echo "us-east-1")
export API_GATEWAY_URL=$(terraform output -raw api_gateway_url)
export S3_FILES_BUCKET=$(terraform output -raw s3_files_bucket_name)
export S3_DATA_BUCKET=$(terraform output -raw s3_data_bucket_name)

echo "ECR Repository: $ECR_REPO"
echo "API Gateway URL: $API_GATEWAY_URL"
echo "S3 Files Bucket: $S3_FILES_BUCKET"
echo "S3 Data Bucket: $S3_DATA_BUCKET"
```

### Step 5: Build and Push Docker Image

```bash
# Navigate to backend directory
cd ../backend

# Get AWS account ID
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build Docker image
docker build -t predictor-model-backend:latest .

# Tag the image for ECR
docker tag predictor-model-backend:latest $ECR_REPO:latest

# Push to ECR
docker push $ECR_REPO:latest
```

### Step 6: Deploy ECS Service

The ECS service should start automatically once the image is pushed. Verify deployment:

```bash
# Get cluster and service names
export CLUSTER_NAME=$(cd ../terraform && terraform output -raw ecs_cluster_name)
export SERVICE_NAME=$(cd ../terraform && terraform output -raw ecs_service_name)

# Check service status
aws ecs describe-services \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region $AWS_REGION

# View running tasks
aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --region $AWS_REGION

# Check logs
aws logs tail /ecs/predictor-model-prod-backend --follow --region $AWS_REGION
```

### Step 7: Test the API

```bash
# Test health endpoint
curl $API_GATEWAY_URL/health

# Expected response:
# {"status":"healthy"}

# Test root endpoint
curl $API_GATEWAY_URL/

# Test API documentation
echo "Open in browser: $API_GATEWAY_URL/docs"
```

### Step 8: Update Amplify Frontend

Update your Amplify environment variables with the new API Gateway URL:

```bash
# Via AWS Console:
# 1. Go to Amplify Console
# 2. Select your app
# 3. Go to Environment variables
# 4. Add/Update: VITE_API_URL = <API_GATEWAY_URL>

# Or via CLI:
aws amplify update-app \
  --app-id d12abg5dtejald \
  --environment-variables VITE_API_URL=$API_GATEWAY_URL \
  --region $AWS_REGION
```

Redeploy your Amplify app to pick up the new environment variable.

## Monitoring and Maintenance

### View Logs

```bash
# ECS Task Logs
aws logs tail /ecs/predictor-model-prod-backend --follow --region $AWS_REGION

# API Gateway Logs
aws logs tail /aws/apigateway/predictor-model-prod --follow --region $AWS_REGION
```

### Check ECS Service

```bash
# Service status
aws ecs describe-services \
  --cluster $CLUSTER_NAME \
  --services $SERVICE_NAME \
  --region $AWS_REGION \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Events:events[0:3]}'

# Task details
aws ecs list-tasks \
  --cluster $CLUSTER_NAME \
  --service-name $SERVICE_NAME \
  --region $AWS_REGION
```

### Update Application

To deploy a new version:

```bash
# Build new image
cd backend
docker build -t predictor-model-backend:latest .

# Tag with version (optional)
docker tag predictor-model-backend:latest $ECR_REPO:v1.0.1
docker tag predictor-model-backend:latest $ECR_REPO:latest

# Push to ECR
docker push $ECR_REPO:v1.0.1
docker push $ECR_REPO:latest

# Force new deployment
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --force-new-deployment \
  --region $AWS_REGION
```

### Scale Service

```bash
# Manually scale
aws ecs update-service \
  --cluster $CLUSTER_NAME \
  --service $SERVICE_NAME \
  --desired-count 2 \
  --region $AWS_REGION

# Auto-scaling is already configured for CPU (70%) and Memory (80%)
```

## Cost Management

### Monitor Costs

```bash
# Check current month costs for ECS
aws ce get-cost-and-usage \
  --time-period Start=$(date -d "$(date +%Y-%m-01)" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE \
  --filter file://<(echo '{
    "Tags": {
      "Key": "Project",
      "Values": ["AI-Predictor"]
    }
  }')
```

### Cost Optimization Tips

1. **Fargate Spot**: Already using 70% cheaper than regular Fargate
2. **Scale to zero**: For dev/staging, scale to 0 when not in use:

   ```bash
   aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 0
   ```

3. **S3 Lifecycle**: Already configured to move to Glacier after 90 days
4. **CloudWatch Logs**: Retention set to 7 days (adjust if needed)

## Troubleshooting

### ECS Tasks Not Starting

1. **Check CloudWatch Logs**:

   ```bash
   aws logs tail /ecs/predictor-model-prod-backend --follow
   ```

2. **Verify ECR Image**:

   ```bash
   aws ecr describe-images --repository-name $CLUSTER_NAME-backend
   ```

3. **Check Task Definition**:

   ```bash
   aws ecs describe-task-definition --task-definition predictor-model-prod-backend
   ```

### API Gateway Issues

1. **Check VPC Link**:

   ```bash
   aws apigatewayv2 get-vpc-links --region $AWS_REGION
   ```

2. **Test ECS Service Directly** (from within VPC):
   - ECS tasks are in private subnets and not publicly accessible
   - Must go through API Gateway

### S3 Access Issues

1. **Verify IAM Role Permissions**:

   ```bash
   aws iam get-role-policy \
     --role-name predictor-model-prod-ecs-task-role \
     --policy-name predictor-model-prod-ecs-task-s3-policy
   ```

2. **Check VPC S3 Endpoint**:

   ```bash
   aws ec2 describe-vpc-endpoints --region $AWS_REGION | grep s3
   ```

## Rollback

If you need to rollback the deployment:

```bash
cd terraform
terraform destroy
```

**Warning**: This will delete all resources including S3 buckets. Make sure to backup data first:

```bash
# Backup S3 buckets
aws s3 sync s3://$S3_FILES_BUCKET ./backup/files/
aws s3 sync s3://$S3_DATA_BUCKET ./backup/data/
```

## Security Considerations

1. **VPC**: All ECS tasks run in private subnets with no direct internet access
2. **S3**: Buckets have public access blocked and use encryption at rest
3. **IAM**: Roles follow least privilege principle
4. **API Gateway**: CORS configured for specific origins only
5. **Secrets**: Use AWS Secrets Manager for sensitive data (not environment variables)

## Next Steps

1. **Set up CI/CD**: Automate deployments with GitHub Actions or AWS CodePipeline
2. **Custom Domain**: Add custom domain to API Gateway
3. **CloudWatch Alarms**: Set up alarms for errors and performance
4. **Backup Strategy**: Implement regular backups for S3 data
5. **Monitoring**: Set up CloudWatch dashboards

## Support

For issues or questions:

- Check CloudWatch logs first
- Review Terraform plan for configuration issues
- Verify all AWS resources are in the same region
- Ensure IAM permissions are correctly set

---

**Estimated Monthly Cost**: $8-15 (for low traffic, couple uses per week)

**Cost Breakdown**:

- API Gateway: $1-3
- VPC Endpoints: $7-10
- ECS Fargate Spot: $4-6
- S3 & CloudWatch: Minimal
