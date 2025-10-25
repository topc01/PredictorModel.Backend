#!/bin/bash
set -e

# Deployment script for AI Predictor Backend
# This script automates the deployment process

echo "🚀 AI Predictor Backend Deployment Script"
echo "=========================================="
echo ""

# Check if required tools are installed
command -v terraform >/dev/null 2>&1 || { echo "❌ Terraform is required but not installed. Aborting." >&2; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "❌ AWS CLI is required but not installed. Aborting." >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Aborting." >&2; exit 1; }

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Function to print colored output
print_success() { echo "✅ $1"; }
print_info() { echo "ℹ️  $1"; }
print_warning() { echo "⚠️  $1"; }
print_error() { echo "❌ $1"; }

# Step 1: Check if terraform.tfvars exists
if [ ! -f "$SCRIPT_DIR/terraform.tfvars" ]; then
    print_warning "terraform.tfvars not found. Creating from example..."
    cp "$SCRIPT_DIR/terraform.tfvars.example" "$SCRIPT_DIR/terraform.tfvars"
    print_info "Please edit terraform.tfvars with your configuration"
    print_info "Then run this script again"
    exit 0
fi

# Step 2: Initialize Terraform
print_info "Initializing Terraform..."
cd "$SCRIPT_DIR"
terraform init

# Step 3: Plan infrastructure
print_info "Planning infrastructure changes..."
terraform plan -out=tfplan

# Step 4: Confirm deployment
read -p "Do you want to apply these changes? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    print_warning "Deployment cancelled"
    exit 0
fi

# Step 5: Apply Terraform
print_info "Applying Terraform configuration..."
terraform apply tfplan
rm tfplan

print_success "Infrastructure deployed successfully!"

# Step 6: Get outputs
print_info "Retrieving infrastructure outputs..."
export ECR_REPO=$(terraform output -raw ecr_repository_url)
export AWS_REGION=$(terraform output -raw aws_region 2>/dev/null || echo "us-east-1")
export API_GATEWAY_URL=$(terraform output -raw api_gateway_url)
export S3_FILES_BUCKET=$(terraform output -raw s3_files_bucket_name)
export S3_DATA_BUCKET=$(terraform output -raw s3_data_bucket_name)
export CLUSTER_NAME=$(terraform output -raw ecs_cluster_name)
export SERVICE_NAME=$(terraform output -raw ecs_service_name)

echo ""
print_info "Infrastructure Details:"
echo "  ECR Repository: $ECR_REPO"
echo "  API Gateway URL: $API_GATEWAY_URL"
echo "  S3 Files Bucket: $S3_FILES_BUCKET"
echo "  S3 Data Bucket: $S3_DATA_BUCKET"
echo ""

# Step 7: Build and push Docker image
read -p "Do you want to build and push the Docker image? (yes/no): " build_confirm
if [ "$build_confirm" == "yes" ]; then
    print_info "Building Docker image..."
    cd "$PROJECT_ROOT/backend"
    
    # Get AWS account ID
    export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    # Login to ECR
    print_info "Logging in to ECR..."
    aws ecr get-login-password --region $AWS_REGION | \
        docker login --username AWS --password-stdin \
        $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
    
    # Build image
    print_info "Building Docker image..."
    docker build -t predictor-model-backend:latest .
    
    # Tag image
    print_info "Tagging image..."
    docker tag predictor-model-backend:latest $ECR_REPO:latest
    docker tag predictor-model-backend:latest $ECR_REPO:$(date +%Y%m%d-%H%M%S)
    
    # Push image
    print_info "Pushing image to ECR..."
    docker push $ECR_REPO:latest
    docker push $ECR_REPO:$(date +%Y%m%d-%H%M%S)
    
    print_success "Docker image pushed successfully!"
    
    # Step 8: Update ECS service
    print_info "Updating ECS service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --force-new-deployment \
        --region $AWS_REGION >/dev/null
    
    print_success "ECS service deployment initiated!"
    print_info "Waiting for service to stabilize (this may take a few minutes)..."
    
    aws ecs wait services-stable \
        --cluster $CLUSTER_NAME \
        --services $SERVICE_NAME \
        --region $AWS_REGION
    
    print_success "Service is now stable!"
fi

# Step 9: Test the deployment
echo ""
print_info "Testing the deployment..."
sleep 5

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" $API_GATEWAY_URL/health)
if [ "$HTTP_CODE" == "200" ]; then
    print_success "Health check passed! API is responding correctly."
else
    print_warning "Health check returned HTTP $HTTP_CODE. The service may still be starting up."
fi

# Final summary
echo ""
echo "=========================================="
echo "🎉 Deployment Complete!"
echo "=========================================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Test your API:"
echo "   curl $API_GATEWAY_URL/health"
echo "   curl $API_GATEWAY_URL/docs"
echo ""
echo "2. Update Amplify frontend with API URL:"
echo "   VITE_API_URL=$API_GATEWAY_URL"
echo ""
echo "3. Monitor logs:"
echo "   aws logs tail /ecs/$CLUSTER_NAME-backend --follow --region $AWS_REGION"
echo ""
echo "4. View API documentation:"
echo "   $API_GATEWAY_URL/docs"
echo ""
print_success "All done! 🚀"

