"""
S3 client module for handling file uploads and downloads.
"""
import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class S3Client:
    """S3 client for file operations"""
    
    def __init__(self):
        """Initialize S3 client with environment variables"""
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.files_bucket = os.getenv("S3_FILES_BUCKET")
        self.data_bucket = os.getenv("S3_DATA_BUCKET")
        
        # Initialize boto3 S3 client
        self.s3_client = boto3.client("s3", region_name=self.aws_region)
        
        logger.info(f"S3 Client initialized - Region: {self.aws_region}")
        logger.info(f"Files bucket: {self.files_bucket}")
        logger.info(f"Data bucket: {self.data_bucket}")
    
    def upload_file(self, file_content: bytes, key: str, bucket_type: str = "files", 
                   content_type: Optional[str] = None) -> bool:
        """
        Upload file to S3
        
        Args:
            file_content: File content as bytes
            key: S3 object key (path/filename)
            bucket_type: Either "files" or "data"
            content_type: MIME type of the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        bucket_name = self.files_bucket if bucket_type == "files" else self.data_bucket
        
        if not bucket_name:
            logger.error(f"Bucket name not configured for type: {bucket_type}")
            return False
        
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=file_content,
                **extra_args
            )
            logger.info(f"Successfully uploaded {key} to {bucket_name}")
            return True
            
        except ClientError as e:
            logger.error(f"Error uploading {key} to S3: {str(e)}")
            return False
    
    def download_file(self, key: str, bucket_type: str = "files") -> Optional[bytes]:
        """
        Download file from S3
        
        Args:
            key: S3 object key (path/filename)
            bucket_type: Either "files" or "data"
            
        Returns:
            bytes: File content if successful, None otherwise
        """
        bucket_name = self.files_bucket if bucket_type == "files" else self.data_bucket
        
        if not bucket_name:
            logger.error(f"Bucket name not configured for type: {bucket_type}")
            return None
        
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            logger.info(f"Successfully downloaded {key} from {bucket_name}")
            return response["Body"].read()
            
        except ClientError as e:
            logger.error(f"Error downloading {key} from S3: {str(e)}")
            return None
    
    def list_files(self, prefix: str = "", bucket_type: str = "files") -> list[str]:
        """
        List files in S3 bucket with given prefix
        
        Args:
            prefix: S3 key prefix to filter results
            bucket_type: Either "files" or "data"
            
        Returns:
            list: List of S3 object keys
        """
        bucket_name = self.files_bucket if bucket_type == "files" else self.data_bucket
        
        if not bucket_name:
            logger.error(f"Bucket name not configured for type: {bucket_type}")
            return []
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )
            
            if "Contents" not in response:
                return []
            
            return [obj["Key"] for obj in response["Contents"]]
            
        except ClientError as e:
            logger.error(f"Error listing files in S3: {str(e)}")
            return []
    
    def delete_file(self, key: str, bucket_type: str = "files") -> bool:
        """
        Delete file from S3
        
        Args:
            key: S3 object key (path/filename)
            bucket_type: Either "files" or "data"
            
        Returns:
            bool: True if successful, False otherwise
        """
        bucket_name = self.files_bucket if bucket_type == "files" else self.data_bucket
        
        if not bucket_name:
            logger.error(f"Bucket name not configured for type: {bucket_type}")
            return False
        
        try:
            self.s3_client.delete_object(Bucket=bucket_name, Key=key)
            logger.info(f"Successfully deleted {key} from {bucket_name}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting {key} from S3: {str(e)}")
            return False
    
    def generate_presigned_url(self, key: str, bucket_type: str = "files", 
                               expiration: int = 3600) -> Optional[str]:
        """
        Generate presigned URL for downloading a file
        
        Args:
            key: S3 object key (path/filename)
            bucket_type: Either "files" or "data"
            expiration: URL expiration time in seconds (default 1 hour)
            
        Returns:
            str: Presigned URL if successful, None otherwise
        """
        bucket_name = self.files_bucket if bucket_type == "files" else self.data_bucket
        
        if not bucket_name:
            logger.error(f"Bucket name not configured for type: {bucket_type}")
            return None
        
        try:
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket_name, "Key": key},
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for {key}")
            return url
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            return None


# Singleton instance
_s3_client: Optional[S3Client] = None

def get_s3_client() -> S3Client:
    """Get S3 client singleton instance"""
    global _s3_client
    if _s3_client is None:
        _s3_client = S3Client()
    return _s3_client

