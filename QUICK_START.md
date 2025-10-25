# Quick Start Guide

## 🚀 Get Your Backend Running in Minutes

### Option 1: Automated Deployment (Recommended)

```bash
cd /Users/topc/Projects/AI-Predictor/PredictorModel.Backend/terraform
./deploy.sh
```

That's it! The script will:

1. Check prerequisites
2. Deploy infrastructure
3. Build and push Docker image
4. Start the ECS service
5. Give you the API URL

### Option 2: Local Development First

Test locally before deploying to AWS:

```bash
cd /Users/topc/Projects/AI-Predictor/PredictorModel.Backend/backend

# Install dependencies
pip install uv
uv sync

# Run the server
uv run uvicorn src.main:app --reload
```

Visit <http://localhost:8000/docs> to test the API.

### Option 3: Manual Deployment

If you prefer step-by-step control:

```bash
# 1. Configure
cd terraform
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Edit with your settings

# 2. Deploy infrastructure
terraform init
terraform apply

# 3. Build and deploy
export ECR_REPO=$(terraform output -raw ecr_repository_url)
cd ../backend
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin ${ECR_REPO%%/*}
docker build -t predictor-model-backend .
docker tag predictor-model-backend:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# 4. Get your API URL
cd ../terraform
terraform output api_gateway_url
```

## 📋 Before You Start

Make sure you have:

- ✅ AWS CLI configured (`aws configure`)
- ✅ Terraform installed (`terraform --version`)
- ✅ Docker running (`docker ps`)

## 🎯 After Deployment

1. **Test your API**:

   ```bash
   export API_URL=$(cd terraform && terraform output -raw api_gateway_url)
   curl $API_URL/health
   ```

2. **Update Amplify** with the API URL:
   - Go to Amplify Console
   - Add environment variable: `VITE_API_URL`
   - Value: Your API Gateway URL
   - Redeploy frontend

3. **Monitor logs**:

   ```bash
   aws logs tail /ecs/predictor-model-prod-backend --follow
   ```

## 💰 Cost

**~$13-21/month** for low traffic (vs $60-80 traditional setup)

Monthly breakdown:

- API Gateway: $1-3
- VPC Endpoints: $7-10
- Fargate Spot: $4-6
- S3 & Logs: $1-2

## 🆘 Need Help?

- **Full documentation**: See [DEPLOYMENT.md](DEPLOYMENT.md)
- **Troubleshooting**: Check CloudWatch logs
- **Questions**: Review [README.md](README.md) and [TERRAFORM_SETUP_SUMMARY.md](TERRAFORM_SETUP_SUMMARY.md)

## 🎉 You're Ready

Choose your path above and get started. The automated deployment script (`./deploy.sh`) is the easiest way to get up and running.
