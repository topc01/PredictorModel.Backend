#!/bin/bash

# Local Development Setup Script
# Sets up your local environment to connect to S3

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║            Local Development Setup with S3                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

cd backend

# Check if AWS CLI is configured
echo -e "${YELLOW}🔍 Checking AWS CLI configuration...${NC}"
if aws sts get-caller-identity &>/dev/null; then
    echo -e "${GREEN}✅ AWS CLI is configured${NC}"
    AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
    AWS_USER=$(aws sts get-caller-identity --query Arn --output text)
    echo "   Account: $AWS_ACCOUNT"
    echo "   User: $AWS_USER"
else
    echo -e "${RED}❌ AWS CLI is not configured${NC}"
    echo ""
    echo "Please run: aws configure"
    echo ""
    echo "You'll need:"
    echo "  - AWS Access Key ID"
    echo "  - AWS Secret Access Key"
    echo "  - Default region: us-east-1"
    exit 1
fi

echo ""

# Check S3 bucket access
echo -e "${YELLOW}🪣 Checking S3 bucket access...${NC}"

BUCKETS=("predictor-model-prod-files" "predictor-model-prod-data")
ALL_ACCESSIBLE=true

for bucket in "${BUCKETS[@]}"; do
    if aws s3 ls "s3://$bucket" &>/dev/null; then
        echo -e "${GREEN}✅ Access to $bucket${NC}"
    else
        echo -e "${RED}❌ No access to $bucket${NC}"
        ALL_ACCESSIBLE=false
    fi
done

if [ "$ALL_ACCESSIBLE" = false ]; then
    echo ""
    echo -e "${YELLOW}⚠️  You don't have access to production buckets.${NC}"
    echo "Options:"
    echo "  1. Request access to production buckets"
    echo "  2. Create local test buckets (recommended for development)"
    echo ""
    read -p "Create local test buckets? (yes/no): " -r
    if [[ $REPLY =~ ^[Yy](es)?$ ]]; then
        echo ""
        echo "Creating test buckets..."
        aws s3 mb s3://predictor-model-local-test-files || true
        aws s3 mb s3://predictor-model-local-test-data || true
        echo -e "${GREEN}✅ Test buckets created${NC}"
        S3_FILES_BUCKET="predictor-model-local-test-files"
        S3_DATA_BUCKET="predictor-model-local-test-data"
    else
        echo "Please configure S3 access and try again."
        exit 1
    fi
else
    S3_FILES_BUCKET="predictor-model-prod-files"
    S3_DATA_BUCKET="predictor-model-prod-data"
fi

echo ""

# Create .env file
echo -e "${YELLOW}📝 Creating .env file...${NC}"

cat > .env << EOF
# AWS Configuration (from AWS CLI)
AWS_REGION=us-east-1

# S3 Buckets
S3_FILES_BUCKET=$S3_FILES_BUCKET
S3_DATA_BUCKET=$S3_DATA_BUCKET

# Storage Configuration
STORAGE_TYPE=s3
STORAGE_BASE_PATH=uploads

# Uncomment to use local filesystem instead of S3
# STORAGE_TYPE=local
# STORAGE_BASE_PATH=./data
EOF

echo -e "${GREEN}✅ .env file created${NC}"
echo ""

# Install dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
uv sync
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Summary
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                  ✅ Setup Complete!                           ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "${GREEN}🚀 Start the development server:${NC}"
echo ""
echo "   cd backend"
echo "   uv run dev"
echo ""
echo "The backend will be available at: http://localhost:8000"
echo ""
echo -e "${GREEN}🧪 Test S3 connection:${NC}"
echo ""
echo "   curl http://localhost:8000/storage/health"
echo ""
echo -e "${GREEN}📚 View API documentation:${NC}"
echo ""
echo "   open http://localhost:8000/docs"
echo ""
echo "For more details, see: LOCAL_DEVELOPMENT.md"
echo ""

