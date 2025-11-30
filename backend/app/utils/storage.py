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
    
    def __init__(self, storage_type: str = "local", base_path: str = "./data", s3_bucket: Optional[str] = None):
        """
        Initialize storage manager.
        
        Args:
            storage_type: 'local' or 's3'
            base_path: Base directory for local storage or S3 prefix
            s3_bucket: S3 bucket name (required if storage_type='s3')
        """
        self.storage_type = storage_type
        self.base_path = base_path
        self.s3_bucket = s3_bucket
        
        if storage_type == "local":
            # Create local directory if it doesn't exist
            Path(base_path).mkdir(parents=True, exist_ok=True)
        elif storage_type == "s3":
            if not s3_bucket:
                raise ValueError("s3_bucket is required when storage_type='s3'")
            # S3 client will be initialized when needed
            self._s3_client = None
    
    @property
    def s3_client(self):
        """Lazy initialization of S3 client."""
        if self._s3_client is None and self.storage_type == "s3":
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
        if self.storage_type == "local":
            filepath = os.path.join(self.base_path, filename)
            df.to_csv(filepath, index=False)
            return filepath
        
        elif self.storage_type == "s3":
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            s3_key = f"{self.base_path}/{filename}"
            
            self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=csv_buffer.getvalue()
            )
            return f"s3://{self.s3_bucket}/{s3_key}"
        
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")
    
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
        if self.storage_type == "local":
            filepath = os.path.join(self.base_path, filename)
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File not found: {filepath}")
            return pd.read_csv(filepath)
        
        elif self.storage_type == "s3":
            s3_key = f"{self.base_path}/{filename}"
            try:
                obj = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
                return pd.read_csv(io.BytesIO(obj['Body'].read()))
            except self.s3_client.exceptions.NoSuchKey:
                raise FileNotFoundError(f"S3 object not found: s3://{self.s3_bucket}/{s3_key}")
        
        else:
            raise ValueError(f"Unsupported storage type: {self.storage_type}")
    
    def exists(self, filename: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            True if file exists, False otherwise
        """
        if self.storage_type == "local":
            filepath = os.path.join(self.base_path, filename)
            return os.path.exists(filepath)
        
        elif self.storage_type == "s3":
            s3_key = f"{self.base_path}/{filename}"
            try:
                self.s3_client.head_object(Bucket=self.s3_bucket, Key=s3_key)
                return True
            except:
                return False
        
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

    def remove_week_from_file(self, filename: str, semana_año: str, column_name: str = "semana_año") -> int:
        """
        Remove rows corresponding to a specific week from a CSV file.
        
        Args:
            filename: Name of the CSV file
            semana_año: Week identifier to remove (e.g., '2025-31')
            column_name: Name of the column containing week identifiers
        Returns:
            Number of rows removed
        """
        df = self.load_csv(filename)
        if column_name not in df.columns:
            raise KeyError(f"Column '{column_name}' not found in {filename}")
        
        mask = df[column_name] == semana_año
        removed = int(mask.sum())
        if removed == 0:
            return 0
        df_filtered = df[~mask].reset_index(drop=True)
        
        self.save_csv(df_filtered, filename)
        return removed

    def remove_last_row_from_file(self, filename: str, n: int = 1) -> int:
        """
        Remove the last n rows from a CSV file.
        
        Args:
            filename: Name of the CSV file
            n: Number of rows to remove from the end
        Returns:
            Number of rows removed
        """
        df = self.load_csv(filename)
        if df.empty:
            return 0

        # Antes de truncar, ordenar por columna de semana ('semana_año') si existe
        if 'semana_año' in df.columns:
            try:
                parts = df['semana_año'].astype(str).str.split('-')
                year = parts.str[0].astype(int)
                week = parts.str[1].astype(int)
                df = df.assign(_sort_year=year, _sort_week=week)
                df = df.sort_values(['_sort_year', '_sort_week']).drop(columns=['_sort_year', '_sort_week']).reset_index(drop=True)
            except Exception:
                df = df.sort_values('semana_año').reset_index(drop=True)

        else:
            date_cols = ['Fecha ingreso', 'fecha ingreso completa', 'fecha_ingreso_completa']
            chosen = None
            for c in date_cols:
                if c in df.columns:
                    chosen = c
                    break

            if chosen:
                try:
                    df[chosen] = pd.to_datetime(df[chosen], errors='coerce')
                    df = df.sort_values(chosen).reset_index(drop=True)
                except Exception:
                    # si falla la conversión, no ordenar
                    pass

        n = min(n, len(df))
        if n == 0:
            return 0

        new_df = df.iloc[:-n].reset_index(drop=True)
        removed = len(df) - len(new_df)
        self.save_csv(new_df, filename)
        return removed

# Global storage manager instance
# Can be configured via environment variables
_storage_type = os.getenv("STORAGE_TYPE", "s3")
_storage_base_path = os.getenv("STORAGE_BASE_PATH", "./data")
_s3_bucket = os.getenv("S3_DATA_BUCKET", None)

storage_manager = StorageManager(
    storage_type=_storage_type,
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

