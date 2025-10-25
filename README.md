# AI Predictor Backend

FastAPI backend for hospital bed occupancy prediction, deployed on AWS with cost-optimized infrastructure.

## Overview

This backend service provides RESTful APIs for:

- Uploading weekly hospital complexity data (Excel files)
- Processing and storing predictions
- Managing patient demand forecasts
- Integration with S3 for data persistence

## Architecture

### AWS Infrastructure (Cost-Optimized)

- **ECS Fargate Spot**: 70% cheaper than regular Fargate
- **API Gateway HTTP API**: Replaces ALB, reduces costs by 80%
- **VPC Endpoints**: Eliminates NAT Gateway (~$32-45/month savings)
- **S3**: File storage and processed data
- **ECR**: Docker image repository

**Estimated Monthly Cost**: $8-15 (vs $60-80 traditional setup)

### Application Stack

- **Framework**: FastAPI 0.118+
- **Runtime**: Python 3.11
- **Package Manager**: uv (fast Python package manager)
- **Dependencies**: pandas, openpyxl, boto3
- **Storage**: AWS S3
- **Container**: Docker

## Quick Start (Local Development)

### Prerequisites

- Python 3.11+
- uv package manager
- Docker (optional, for containerized development)

### Setup

1. **Clone the repository**:

   ```bash
   cd /Users/topc/Projects/AI-Predictor/PredictorModel.Backend
   ```

2. **Install dependencies**:

   ```bash
   cd backend
   pip install uv
   uv sync
   ```

3. **Run the development server**:

   ```bash
   uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Access the API**:
   - API: <http://localhost:8000>
   - Interactive docs: <http://localhost:8000/docs>
   - OpenAPI spec: <http://localhost:8000/openapi.json>

### Using Docker Compose

```bash
docker-compose up
```

The API will be available at <http://localhost:8000>

## API Endpoints

### Health Check

```http
GET /health
```

### Submit Weekly Data

```http
POST /send
Content-Type: application/json

{
  "alta": { "demanda_pacientes": 50, ... },
  "baja": { "demanda_pacientes": 30, ... },
  ...
}
```

### Upload Excel File

```http
POST /upload
Content-Type: multipart/form-data

file: [Excel file]
```

### Download Template

```http
GET /template
```

For detailed API documentation, visit `/docs` when the server is running.

## Deployment

### AWS Deployment (Recommended)

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete deployment instructions.

**Quick deployment**:

```bash
# 1. Deploy infrastructure
cd terraform
terraform init
terraform apply

# 2. Build and push Docker image
cd ../backend
export ECR_REPO=$(cd ../terraform && terraform output -raw ecr_repository_url)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${ECR_REPO%%/*}
docker build -t predictor-model-backend:latest .
docker tag predictor-model-backend:latest $ECR_REPO:latest
docker push $ECR_REPO:latest

# 3. Get API Gateway URL
cd ../terraform
terraform output api_gateway_url
```

## Environment Variables

### Required for AWS Deployment

```bash
AWS_REGION=us-east-1
S3_FILES_BUCKET=predictor-model-prod-files
S3_DATA_BUCKET=predictor-model-prod-data
CORS_ORIGINS=https://your-frontend.amplifyapp.com
```

These are automatically configured by Terraform in the ECS task definition.

### Optional for Local Development

For local development without S3, the application will work without these variables (S3 operations will be skipped).

## Project Structure

```
PredictorModel.Backend/
├── backend/
│   ├── src/
│   │   ├── main.py              # FastAPI application
│   │   ├── s3_client.py         # S3 integration
│   │   └── routes/
│   │       └── data.py          # Data endpoints
│   ├── Dockerfile               # Container definition
│   ├── pyproject.toml           # Python dependencies
│   └── uv.lock                  # Locked dependencies
├── terraform/                    # AWS infrastructure
│   ├── main.tf                  # Root module
│   ├── variables.tf             # Input variables
│   ├── outputs.tf               # Output values
│   └── modules/                 # Terraform modules
│       ├── networking/          # VPC, subnets, endpoints
│       ├── ecs/                 # ECS cluster, tasks
│       ├── ecr/                 # Container registry
│       ├── s3/                  # Storage buckets
│       ├── api-gateway/         # API Gateway
│       ├── iam/                 # IAM roles
│       └── security/            # Security groups
├── docker-compose.yaml          # Local development
├── DEPLOYMENT.md                # Deployment guide
└── README.md                    # This file
```

## Development

### Adding Dependencies

```bash
cd backend
uv add package-name
```

This automatically updates `pyproject.toml` and `uv.lock`.

### Running Tests

```bash
uv run pytest
```

### Code Style

```bash
# Format code
uv run black src/

# Lint
uv run ruff check src/
```

## S3 Integration

The backend automatically saves:

1. **Uploaded Excel files** → `s3://predictor-model-{env}-files/uploads/{date}/{id}_{filename}`
2. **JSON submissions** → `s3://predictor-model-{env}-data/submissions/{date}/{id}.json`
3. **Processed data** → `s3://predictor-model-{env}-data/processed/{date}/{id}.json`

Files are organized by date for easy management and lifecycle policies.

## Monitoring

### CloudWatch Logs

- **ECS Logs**: `/ecs/predictor-model-{env}-backend`
- **API Gateway Logs**: `/aws/apigateway/predictor-model-{env}`

### Metrics

- ECS Container Insights enabled
- Auto-scaling based on CPU (70%) and Memory (80%)
- API Gateway metrics in CloudWatch

## Cost Optimization Features

1. **Fargate Spot**: 70% cheaper than regular Fargate, with automatic fallback
2. **No NAT Gateway**: VPC endpoints for S3, ECR, CloudWatch
3. **API Gateway HTTP API**: Cheaper than REST API and ALB
4. **S3 Lifecycle**: Auto-archive to Glacier after 90 days
5. **Log Retention**: 7 days (adjustable)
6. **Auto-scaling**: Scale down during low usage

**Result**: ~80% cost reduction vs traditional setup

## Troubleshooting

### Local Development Issues

**Port already in use**:

```bash
lsof -ti:8000 | xargs kill -9
```

**Dependencies not installing**:

```bash
rm -rf .venv
uv sync --force
```

### AWS Deployment Issues

See [DEPLOYMENT.md](./DEPLOYMENT.md#troubleshooting) for AWS-specific troubleshooting.

## Security

- All ECS tasks run in private subnets
- S3 buckets have public access blocked
- Encryption at rest for S3 and ECR
- IAM roles follow least privilege
- CORS configured for specific origins only

## Contributing

1. Create a feature branch
2. Make your changes
3. Test locally with `docker-compose up`
4. Submit a pull request

## License

Internal project for UC Christus.

## Support

For issues or questions:

- Check CloudWatch logs
- Review `/docs` endpoint for API documentation
- See [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment help

---

**Built with**: FastAPI, AWS ECS, Terraform, Python 3.11
