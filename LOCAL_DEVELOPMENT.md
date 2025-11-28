# Local Development with S3

## 🏠 Running Backend Locally with S3 Access

This guide shows you how to run the backend on your local machine with full S3 connectivity.

---

## 📋 Prerequisites

- AWS CLI configured with credentials
- Python 3.11+
- `uv` package manager

---

## 🔧 Step 1: Configure AWS Credentials

### Option A: Use AWS CLI (Recommended)

If you haven't already:

```bash
aws configure
```

Enter your AWS credentials:

- Access Key ID
- Secret Access Key
- Default region: `us-east-1`
- Output format: `json`

### Option B: Use Environment Variables

Create a `.env` file in the `backend` directory:

```bash
cd /Users/topc/Projects/AI-Predictor/PredictorModel.Backend/backend
touch .env
```

Add these variables:

```env
# AWS Configuration
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_REGION=us-east-1

# S3 Buckets (Production)
S3_FILES_BUCKET=predictor-model-prod-files
S3_DATA_BUCKET=predictor-model-prod-data

# Or use different buckets for local testing if you prefer
# S3_FILES_BUCKET=your-local-test-files-bucket
# S3_DATA_BUCKET=your-local-test-data-bucket

# Auth0 Configuration
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_API_AUDIENCE=https://your-api-identifier
AUTH0_ISSUER=https://your-tenant.auth0.com/
AUTH0_ALGORITHMS=RS256

# Auth0 Management API (for user management)
AUTH0_MANAGEMENT_API_DOMAIN=your-tenant.auth0.com
AUTH0_MANAGEMENT_API_CLIENT_ID=your-m2m-client-id
AUTH0_MANAGEMENT_API_CLIENT_SECRET=your-m2m-client-secret
```

---

## 🔑 Step 2: Create IAM User for Local Development (Optional)

It's best practice to use a separate IAM user for local development:

```bash
# Create user
aws iam create-user --user-name local-dev-user \
  --tags Key=Purpose,Value=LocalDevelopment

# Create policy
cat > /tmp/local-dev-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::predictor-model-prod-files",
        "arn:aws:s3:::predictor-model-prod-files/*",
        "arn:aws:s3:::predictor-model-prod-data",
        "arn:aws:s3:::predictor-model-prod-data/*"
      ]
    }
  ]
}
EOF

# Create and attach policy
aws iam create-policy \
  --policy-name LocalDevS3Access \
  --policy-document file:///tmp/local-dev-policy.json

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws iam attach-user-policy \
  --user-name local-dev-user \
  --policy-arn arn:aws:iam::${AWS_ACCOUNT_ID}:policy/LocalDevS3Access

# Create access keys
aws iam create-access-key --user-name local-dev-user
```

Use these credentials in your `.env` file or AWS CLI profile.

---

## 🚀 Step 3: Install Dependencies

```bash
cd /Users/topc/Projects/AI-Predictor/PredictorModel.Backend/backend

# Install dependencies with uv
uv sync
```

---

## 🏃 Step 4: Run the Backend

### Using the new uv script

```bash
uv run dev
```

Or manually:

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

Your backend will be available at: <http://localhost:8000>

---

## 🧪 Step 5: Test S3 Connection

### Test the storage health endpoint

```bash
curl http://localhost:8000/storage/health
```

You should see:

```json
{
  "status": "healthy",
  "message": "All S3 buckets are accessible",
  "buckets": {
    "files": {
      "name": "predictor-model-prod-files",
      "accessible": true,
      "exists": true,
      "region": "us-east-1"
    },
    "data": {
      "name": "predictor-model-prod-data",
      "accessible": true,
      "exists": true,
      "region": "us-east-1"
    }
  }
}
```

### Test other endpoints

```bash
# Health check
curl http://localhost:8000/health

# API docs
open http://localhost:8000/docs
```

---

## 📁 Using S3 in Your Code

The backend already has S3 utilities configured. Here's how to use them:

### Example: Upload a file to S3

```python
from src.utils.storage import storage_manager
import pandas as pd

# Create some data
df = pd.DataFrame({
    'column1': [1, 2, 3],
    'column2': ['a', 'b', 'c']
})

# Save to S3
path = storage_manager.save_csv(df, 'test_data.csv')
print(f"Saved to: {path}")

# Load from S3
loaded_df = storage_manager.load_csv('test_data.csv')
print(loaded_df)
```

### Configure storage type

The `StorageManager` uses environment variables:

```env
# Use S3 (default in production)
STORAGE_TYPE=s3
S3_BUCKET=predictor-model-prod-files
STORAGE_BASE_PATH=uploads

# Or use local filesystem (for testing)
STORAGE_TYPE=local
STORAGE_BASE_PATH=./data
```

---

## 🔍 Troubleshooting

### Error: "Access Denied"

**Solution**: Check your IAM permissions. Your user needs `s3:GetObject`, `s3:PutObject`, and `s3:ListBucket` permissions.

```bash
# Test AWS credentials
aws sts get-caller-identity

# Test S3 access
aws s3 ls s3://predictor-model-prod-files/
```

### Error: "Bucket does not exist"

**Solution**: Verify the bucket names in your environment variables match the actual bucket names.

```bash
# List your buckets
aws s3 ls

# Check Terraform outputs
cd /Users/topc/Projects/AI-Predictor/terraform
terraform output s3_files_bucket_name
terraform output s3_data_bucket_name
```

### Error: "No module named 'boto3'"

**Solution**: Make sure dependencies are installed:

```bash
cd /Users/topc/Projects/AI-Predictor/PredictorModel.Backend/backend
uv sync
```

---

## 🌐 Local + S3 Configuration Summary

| Component | Local Dev | Production (ECS) |
|-----------|-----------|------------------|
| **Backend** | Running on localhost:8000 | Running in ECS |
| **S3 Access** | ✅ Via AWS credentials | ✅ Via IAM role |
| **Database** | (Not configured yet) | (Not configured yet) |
| **API Gateway** | ❌ Direct access | ✅ Yes |
| **Environment** | `.env` file | ECS task definition |

---

## 💡 Best Practices

### 1. Use Separate Buckets for Local Testing

Instead of using production buckets, create test buckets:

```bash
aws s3 mb s3://predictor-model-local-test-files
aws s3 mb s3://predictor-model-local-test-data
```

Update your `.env`:

```env
S3_FILES_BUCKET=predictor-model-local-test-files
S3_DATA_BUCKET=predictor-model-local-test-data
```

### 2. Don't Commit .env File

The `.env` file should already be in `.gitignore`. Verify:

```bash
cd /Users/topc/Projects/AI-Predictor/PredictorModel.Backend/backend
echo ".env" >> .gitignore
```

### 3. Use AWS CLI Profiles

If you have multiple AWS accounts:

```bash
# Configure a profile
aws configure --profile local-dev

# Use in your code
export AWS_PROFILE=local-dev
```

---

## 🎯 Quick Start Summary

```bash
# 1. Configure AWS credentials
aws configure

# 2. Set environment variables
cd /Users/topc/Projects/AI-Predictor/PredictorModel.Backend/backend
cat > .env << EOF
AWS_REGION=us-east-1
S3_FILES_BUCKET=predictor-model-prod-files
S3_DATA_BUCKET=predictor-model-prod-data
EOF

# 3. Install dependencies
uv sync

# 4. Run the backend
uv run dev

# 5. Test S3 connection
curl http://localhost:8000/storage/health
```

---

## ✅ You're Ready

Your local development environment is now connected to S3. You can:

- ✅ Run the backend locally
- ✅ Access S3 buckets
- ✅ Test file uploads/downloads
- ✅ Develop without deploying

For production deployments, just push to the `main` branch and let CI/CD handle it! 🚀
