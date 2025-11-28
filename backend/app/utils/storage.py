"""
Storage management for CSV files.

Supports both local filesystem (for development) and S3 (for production/Lambda).
"""

import os
import io
from pathlib import Path
from typing import Optional, Dict
import pandas as pd
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()


class StorageManager:
    """
    Manages storage of CSV files for historical data.
    
    In development: Uses local filesystem
    In production: Uses S3 (to be implemented)
    """
    
    def __init__(self, base_path: str = "./data", s3_bucket: Optional[str] = None):
        """
        Initialize storage manager.
        
        Args:
            base_path: Base directory for local storage or S3 prefix
            s3_bucket: S3 bucket name (required if storage_type='s3')
        """
        self.base_path = base_path
        self.s3_bucket = s3_bucket
        
        if not s3_bucket:
            raise ValueError("s3_bucket is required when storage_type='s3'")
            # S3 client will be initialized when needed
            self._s3_client = None
    
    @property
    def s3_client(self):
        """Lazy initialization of S3 client."""
        if self._s3_client is None:
            import boto3
            self._s3_client = boto3.client('s3')
        return self._s3_client
    
    def save_csv(self, df: pd.DataFrame, filename: str) -> str:
        """
        Save DataFrame as CSV.
        
        Args:
            df: DataFrame to save
            filename: Name of the file (e.g., 'Alta.csv')
            
        Returns:
            Path or S3 URI where file was saved
        """
        
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        s3_key = f"{self.base_path}/{filename}"
            
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=s3_key,
            Body=csv_buffer.getvalue()
        )
        return f"s3://{self.s3_bucket}/{s3_key}"
    
    def load_csv(self, filename: str) -> pd.DataFrame:
        """
        Load CSV as DataFrame.
        
        Args:
            filename: Name of the file to load
            
        Returns:
            DataFrame with the data
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        
        s3_key = f"{self.base_path}/{filename}"
        try:
            obj = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
            return pd.read_csv(io.BytesIO(obj['Body'].read()))
        except self.s3_client.exceptions.NoSuchKey:
            raise FileNotFoundError(f"S3 object not found: s3://{self.s3_bucket}/{s3_key}")

    def save_model(self, model, metadata) -> None:
        """
        Save a model to the storage.
        
        Args:
            model: Model to save
            metadata: Metadata to save with the model
        """
        version = metadata.get("version")
        complexity = metadata.get("complexity")
        model_path = f"models/{complexity}/{version}/model.pkl"
        metadata_path = f"models/{complexity}/{version}/metadata.json"

        self.s3_client.put_object(Bucket=self.s3_bucket, Key=model_path, Body=model)
        self.s3_client.put_object(Bucket=self.s3_bucket, Key=metadata_path, Body=json.dumps(metadata))
        
    
    def exists(self, filename: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            True if file exists, False otherwise
        """
        s3_key = f"{self.base_path}/{filename}"
        try:
            self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
            return True
        except:
            return False
    
    def save_multiple_csvs(self, dfs_dict: Dict[str, pd.DataFrame]) -> Dict[str, str]:
        """
        Save multiple DataFrames as CSVs.
        
        Args:
            dfs_dict: Dictionary mapping filenames to DataFrames
            
        Returns:
            Dictionary mapping filenames to saved paths/URIs
        """
        results = {}
        for filename, df in dfs_dict.items():
            if df is not None:
                path = self.save_csv(df, filename)
                results[filename] = path
        return results


# Global storage manager instance
# Can be configured via environment variables
_storage_base_path = os.getenv("STORAGE_BASE_PATH", "./data")
_s3_bucket = os.getenv("S3_DATA_BUCKET", None)

storage_manager = StorageManager(
    base_path=_storage_base_path,
    s3_bucket=_s3_bucket
)


def check_bucket_access(bucket_name: str) -> Dict[str, any]:
    """
    Check if a bucket exists and is accessible.
    
    Returns:
        dict with 'accessible' (bool), 'error' (str or None), and 'exists' (bool)
    """
    try:
        s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        s3_client.head_bucket(Bucket=bucket_name)
        return {
            'accessible': True,
            'exists': True,
            'error': None
        }
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code == '404':
            return {
                'accessible': False,
                'exists': False,
                'error': 'Bucket does not exist'
            }
        elif error_code == '403':
            return {
                'accessible': False,
                'exists': True,
                'error': 'Access denied - check IAM permissions'
            }
        else:
            return {
                'accessible': False,
                'exists': None,
                'error': f'Client error: {error_code}'
            }
    except BotoCoreError as e:
        return {
            'accessible': False,
            'exists': None,
            'error': f'BotoCore error: {str(e)}'
        }
    except Exception as e:
        return {
            'accessible': False,
            'exists': None,
            'error': f'Unexpected error: {str(e)}'
        }


def get_bucket_info(bucket_name: str) -> Optional[Dict]:
    """
    Get basic information about a bucket (region, creation date).
    
    Returns None if bucket is not accessible.
    """
    try:
        s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION', 'us-east-1'))
        
        # Get bucket location
        location_response = s3_client.get_bucket_location(Bucket=bucket_name)
        region = location_response.get('LocationConstraint') or 'us-east-1'
        
        return {
            'region': region,
            'name': bucket_name
        }
    except Exception:
        return None

