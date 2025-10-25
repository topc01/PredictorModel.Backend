# Terraform Infrastructure Setup - Summary

## ✅ What Has Been Created

### 1. Complete Terraform Infrastructure (`terraform/` directory)

#### Root Configuration Files

- **`main.tf`**: Root module orchestrating all infrastructure components
- **`variables.tf`**: Input variables for customization
- **`outputs.tf`**: Infrastructure outputs (URLs, bucket names, etc.)
- **`backend.tf`**: Remote state configuration (commented, ready to use)
- **`terraform.tfvars.example`**: Example configuration file
- **`.gitignore`**: Ignores sensitive Terraform files

#### Infrastructure Modules

**1. Networking Module** (`modules/networking/`)

- VPC with public and private subnets (2 AZs)
- Internet Gateway for public subnets
- **VPC Gateway Endpoint for S3** (free, no NAT Gateway needed)
- **VPC Interface Endpoints** for:
  - ECR API (com.amazonaws.{region}.ecr.api)
  - ECR Docker (com.amazonaws.{region}.ecr.dkr)
  - CloudWatch Logs (com.amazonaws.{region}.logs)
- Security groups for VPC endpoints
- **Cost Savings**: ~$32-45/month (eliminates NAT Gateway)

**2. Security Module** (`modules/security/`)

- Security group for ECS tasks (allows traffic from API Gateway)
- Security group for API Gateway VPC Link
- Proper ingress/egress rules for secure communication

**3. S3 Module** (`modules/s3/`)

- **Files Bucket**: For uploaded Excel files
  - Versioning enabled
  - Server-side encryption (AES256)
  - Lifecycle policy (Glacier after 90 days, delete after 365 days)
  - CORS configuration for Amplify
  - Public access blocked
- **Data Bucket**: For processed predictions and results
  - Versioning enabled
  - Server-side encryption (AES256)
  - CORS configuration for Amplify
  - Public access blocked

**4. ECR Module** (`modules/ecr/`)

- ECR repository for backend Docker images
- Image scanning on push enabled
- Lifecycle policy (keeps last 5 images)
- Encryption at rest

**5. IAM Module** (`modules/iam/`)

- **ECS Task Execution Role**: For pulling images, writing logs
- **ECS Task Role**: For application (S3 access, CloudWatch metrics)
- Least privilege policies
- Proper assume role policies

**6. ECS Module** (`modules/ecs/`)

- ECS Cluster with Container Insights enabled
- **Fargate Spot capacity provider** (70% cost savings)
  - 100% weight on FARGATE_SPOT
  - Automatic fallback to FARGATE if needed
- Task Definition:
  - Configurable CPU (default: 512 = 0.5 vCPU)
  - Configurable Memory (default: 1024 MB)
  - Environment variables for S3 buckets
  - Health checks configured
- ECS Service:
  - Service Discovery via AWS Cloud Map
  - Auto-scaling (CPU 70%, Memory 80%)
  - Min: 1, Max: 2 tasks
  - No direct ALB attachment (uses API Gateway)
- CloudWatch Log Group (7-day retention)

**7. API Gateway Module** (`modules/api-gateway/`)

- **API Gateway HTTP API** (cheaper than REST API)
- VPC Link for private ECS access
- Routes:
  - `ANY /{proxy+}` → Forward all requests to ECS
  - `GET /health` → Health check
  - `GET /` → Root endpoint
- CORS configuration for Amplify origins
- CloudWatch access logs enabled
- Throttling configured (100 burst, 50 rate limit)
- **Cost**: ~$1-3/month vs ALB ~$16-20/month

### 2. Backend Application Updates

#### New Files

- **`backend/src/s3_client.py`**: Complete S3 client implementation
  - Upload files to S3
  - Download files from S3
  - List files
  - Delete files
  - Generate presigned URLs
  - Singleton pattern for efficiency

#### Updated Files

- **`backend/src/main.py`**:
  - Added environment variable loading (dotenv)
  - S3 client initialization on startup
  - Enhanced logging
  - CORS configuration from environment
  - Startup event handler

- **`backend/src/routes/data.py`**:
  - `/send` endpoint: Now saves JSON data to S3
  - `/upload` endpoint: Saves Excel files to S3, processes data, saves results
  - UUID-based file identification
  - Organized S3 structure: `uploads/{date}/{id}_filename`
  - Enhanced logging

- **`backend/pyproject.toml`**:
  - Added `boto3>=1.35.0` for AWS S3
  - Added `python-dotenv>=1.0.0` for environment variables

### 3. Documentation

- **`README.md`**: Complete project documentation
- **`DEPLOYMENT.md`**: Step-by-step deployment guide
- **`terraform/README.md`**: Terraform-specific documentation
- **`TERRAFORM_SETUP_SUMMARY.md`**: This file

### 4. Deployment Scripts

- **`terraform/deploy.sh`**: Automated deployment script
  - Checks prerequisites
  - Initializes Terraform
  - Plans and applies infrastructure
  - Builds and pushes Docker image
  - Updates ECS service
  - Tests deployment

## 📊 Cost Optimization Summary

### Before Optimization

| Component | Monthly Cost |
|-----------|-------------|
| ALB | $16-20 |
| NAT Gateway | $32-45 |
| ECS Fargate (standard) | $15-20 |
| **Total** | **$63-85** |

### After Optimization

| Component | Monthly Cost |
|-----------|-------------|
| API Gateway HTTP API | $1-3 |
| VPC Interface Endpoints (3x) | $7-10 |
| ECS Fargate Spot | $4-6 |
| S3 & CloudWatch | $1-2 |
| **Total** | **$13-21** |

### Savings

- **Monthly**: ~$50-65 (75-80% reduction)
- **Annual**: ~$600-780

## 🚀 How to Deploy

### Quick Start (Automated)

```bash
cd /Users/topc/Projects/AI-Predictor/PredictorModel.Backend/terraform
./deploy.sh
```

The script will guide you through:

1. Creating `terraform.tfvars` (if needed)
2. Deploying infrastructure
3. Building and pushing Docker image
4. Updating ECS service
5. Testing the deployment

### Manual Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed step-by-step instructions.

### Minimal Steps

```bash
# 1. Configure variables
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars

# 2. Deploy infrastructure
terraform init
terraform apply

# 3. Build and push image
cd ../backend
export ECR_REPO=$(cd ../terraform && terraform output -raw ecr_repository_url)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${ECR_REPO%%/*}
docker build -t predictor-model-backend:latest .
docker tag predictor-model-backend:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# 4. Get API URL
cd ../terraform
terraform output api_gateway_url
```

## 📁 File Structure

```
PredictorModel.Backend/
├── backend/
│   ├── src/
│   │   ├── main.py                    # ✅ Updated with S3 integration
│   │   ├── s3_client.py               # ✅ New S3 client
│   │   └── routes/
│   │       └── data.py                # ✅ Updated with S3 storage
│   ├── Dockerfile                     # Existing
│   ├── pyproject.toml                 # ✅ Updated with boto3
│   └── uv.lock                        # Will regenerate on install
├── terraform/                         # ✅ New directory
│   ├── main.tf                        # Root module
│   ├── variables.tf                   # Input variables
│   ├── outputs.tf                     # Outputs
│   ├── backend.tf                     # State configuration
│   ├── terraform.tfvars.example       # Example config
│   ├── .gitignore                     # Terraform gitignore
│   ├── README.md                      # Terraform docs
│   ├── deploy.sh                      # Deployment script
│   └── modules/
│       ├── networking/                # VPC, endpoints
│       ├── security/                  # Security groups
│       ├── s3/                        # S3 buckets
│       ├── ecr/                       # Container registry
│       ├── iam/                       # IAM roles
│       ├── ecs/                       # ECS cluster, services
│       └── api-gateway/               # API Gateway
├── docker-compose.yaml                # Existing
├── README.md                          # ✅ Updated
├── DEPLOYMENT.md                      # ✅ New
└── TERRAFORM_SETUP_SUMMARY.md         # This file

Each module contains:
- main.tf (resources)
- variables.tf (inputs)
- outputs.tf (outputs)
```

## 🔧 Environment Variables

The ECS task definition automatically configures:

```bash
AWS_REGION=us-east-1                           # From Terraform
S3_FILES_BUCKET=predictor-model-{env}-files    # From Terraform
S3_DATA_BUCKET=predictor-model-{env}-data      # From Terraform
PYTHONUNBUFFERED=1                             # For logging
```

For local development, create a `.env` file:

```bash
# Optional for local dev (S3 features will be disabled if not set)
AWS_REGION=us-east-1
S3_FILES_BUCKET=
S3_DATA_BUCKET=
CORS_ORIGINS=http://localhost:5173
```

## 🔐 Security Features

1. **Network Security**
   - ECS tasks in private subnets only
   - No direct internet access (VPC endpoints)
   - Security groups with minimal required access

2. **Data Security**
   - S3 encryption at rest (AES256)
   - S3 public access blocked
   - ECR encryption enabled
   - Versioning on S3 buckets

3. **Access Control**
   - IAM roles with least privilege
   - No long-lived credentials in code
   - Task roles for application permissions
   - Execution roles for AWS service access

4. **API Security**
   - CORS configured for specific origins
   - API Gateway throttling enabled
   - CloudWatch logging for audit trails

## 📊 Monitoring

### CloudWatch Logs

- **ECS Tasks**: `/ecs/predictor-model-{env}-backend`
- **API Gateway**: `/aws/apigateway/predictor-model-{env}`

### Metrics

- ECS Container Insights enabled
- API Gateway metrics automatic
- Custom metrics can be added via CloudWatch

### Alarms (Recommended to Add)

```bash
# Example: High error rate alarm
aws cloudwatch put-metric-alarm \
  --alarm-name predictor-high-errors \
  --alarm-description "Alert on high error rate" \
  --metric-name 5XXError \
  --namespace AWS/ApiGateway \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 10
```

## 🔄 CI/CD Integration (Future)

The infrastructure is ready for CI/CD integration:

### GitHub Actions Example

```yaml
name: Deploy to AWS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Login to ECR
        run: |
          aws ecr get-login-password | docker login --username AWS --password-stdin ${{ secrets.ECR_REPO }}
      
      - name: Build and push
        run: |
          docker build -t ${{ secrets.ECR_REPO }}:${{ github.sha }} .
          docker push ${{ secrets.ECR_REPO }}:${{ github.sha }}
      
      - name: Update ECS
        run: |
          aws ecs update-service --cluster ${{ secrets.CLUSTER_NAME }} \
            --service ${{ secrets.SERVICE_NAME }} --force-new-deployment
```

## 🛠️ Maintenance

### Update Application

```bash
cd backend
docker build -t predictor-model-backend:latest .
docker tag predictor-model-backend:latest $ECR_REPO:latest
docker push $ECR_REPO:latest
aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --force-new-deployment
```

### Scale Service

```bash
# Manual scale
aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 2

# Scale to zero (for dev environments)
aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 0
```

### Update Infrastructure

```bash
cd terraform
# Edit .tf files
terraform plan
terraform apply
```

### View Logs

```bash
aws logs tail /ecs/predictor-model-{env}-backend --follow
```

## ✅ Pre-Deployment Checklist

Before running `terraform apply`:

- [ ] AWS CLI configured with correct credentials
- [ ] Correct AWS region set in `terraform.tfvars`
- [ ] CORS origins updated with actual Amplify URLs
- [ ] Terraform >= 1.5.0 installed
- [ ] Docker installed and running
- [ ] Backend dependencies updated (`cd backend && uv sync`)

## 🎯 Next Steps

1. **Deploy Infrastructure**: Run `./terraform/deploy.sh`
2. **Update Amplify**: Add API Gateway URL to environment variables
3. **Set Up Monitoring**: Create CloudWatch alarms
4. **Custom Domain** (Optional): Add custom domain to API Gateway
5. **CI/CD** (Optional): Set up GitHub Actions or AWS CodePipeline

## 📞 Support

If you encounter issues:

1. **Check Terraform output**: Review any error messages
2. **Check CloudWatch Logs**: Look for application errors
3. **Verify AWS Permissions**: Ensure IAM user has required permissions
4. **Review Documentation**: See DEPLOYMENT.md for detailed troubleshooting

## 🎉 Summary

You now have a complete, production-ready, cost-optimized AWS infrastructure for your FastAPI backend:

- ✅ 75-80% cost reduction vs traditional setup
- ✅ Auto-scaling for reliability
- ✅ S3 integration for data persistence
- ✅ Secure networking with VPC endpoints
- ✅ Monitoring and logging configured
- ✅ Ready for CI/CD integration
- ✅ Comprehensive documentation

**Total estimated monthly cost for low traffic**: $13-21
**Deployment time**: ~10-15 minutes

Ready to deploy! 🚀
