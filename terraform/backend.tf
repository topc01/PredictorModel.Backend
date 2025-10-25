# Terraform backend configuration for storing state in S3
# Uncomment and configure after creating the S3 bucket for state

# terraform {
#   backend "s3" {
#     bucket         = "predictor-model-terraform-state"
#     key            = "predictor-model/terraform.tfstate"
#     region         = "us-east-1"
#     encrypt        = true
#     dynamodb_table = "predictor-model-terraform-locks"
#   }
# }

# To set up the backend:
# 1. Create S3 bucket: aws s3 mb s3://predictor-model-terraform-state
# 2. Enable versioning: aws s3api put-bucket-versioning --bucket predictor-model-terraform-state --versioning-configuration Status=Enabled
# 3. Create DynamoDB table: aws dynamodb create-table --table-name predictor-model-terraform-locks --attribute-definitions AttributeName=LockID,AttributeType=S --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST
# 4. Uncomment the backend configuration above
# 5. Run: terraform init -migrate-state

