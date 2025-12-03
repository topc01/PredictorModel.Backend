"""
Storage management for CSV files.

Supports S3.
"""

import os
import io
from pathlib import Path
from typing import Optional, Dict
import pandas as pd
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from dotenv import load_dotenv
import logging
from datetime import datetime

from app.core.config import settings

# Load environment variables from .env file (for local development)
load_dotenv()

logger = logging.getLogger(__name__)

class StorageManager:
    """
    Manages storage of CSV files for historical data.
    
    Uses S3.
    """
    
    def __init__(self, env: Optional[str] = "local", s3_bucket: Optional[str] = None):
        """
        Initialize storage manager.
        
        Args:
            env: Environment (local or s3)
            s3_bucket: S3 bucket name (required if storage_type='s3')
        """
        self.env = env
        self.s3_bucket = s3_bucket
        self._s3_client = None  # Lazy initialization
        self.base_dir = "data"  # Base directory for local storage
        logger.info(f"StorageManager initialized with env={env}, s3_bucket={s3_bucket}, base_dir={self.base_dir}")
        
        # Only validate s3_bucket if not in local mode
        if env != "local" and not s3_bucket:
            raise ValueError("s3_bucket is required when env is not 'local'")
    
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
        s3_key = f"{self.base_dir}/{filename}"
        if self.env == "local":
            # Always use data/ directory for local storage
            local_path = os.path.join(self.base_dir, filename)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'w') as f:
                f.write(csv_buffer.getvalue())
            return local_path
            
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
        
        s3_key = f"{self.base_dir}/{filename}"
        try:
            if self.env == "local":
                # Always use data/ directory for local storage
                local_path = os.path.join(self.base_dir, filename)
                with open(local_path, 'r') as f:
                    return pd.read_csv(f)
            obj = self.s3_client.get_object(Bucket=self.s3_bucket, Key=s3_key)
            return pd.read_csv(io.BytesIO(obj['Body'].read()))
        except self.s3_client.exceptions.NoSuchKey:
            raise FileNotFoundError(f"S3 object not found: s3://{self.s3_bucket}/{s3_key}")
        except FileNotFoundError:
            raise FileNotFoundError(f"Local file not found: {os.path.join(self.base_dir, filename)}")
        
    def exists(self, filename: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            filename: Name of the file to check
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            if self.env == "local":
                logger.info(f"Checking local file: {os.path.join(self.base_dir, filename)}")
                # Always use data/ directory for local storage
                local_path = os.path.join(self.base_dir, filename)
                return os.path.exists(local_path)
            
            logger.info(f"Checking S3 file: s3://{self.s3_bucket}/{filename}")
            self.s3_client.head_object(Bucket=self.s3_bucket, Key=filename)
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

    def remove_week_from_file(
        self,
        filename: str,
        semana_año: str ) -> int:
        """
        Elimina todas las filas de un CSV donde `column_name == semana_año`
        """

        df = self.load_csv(filename)
        column_name: str = "semana_año"
        if column_name not in df.columns:
            raise KeyError(f"Column '{column_name}' not found in {filename}")

        mask = df[column_name].astype(str) == str(semana_año)
        removed = int(mask.sum())

        if removed == 0:
            return 0

        df_filtered = df.loc[~mask].reset_index(drop=True)
        self.save_csv(df_filtered, filename)

        return removed

    def remove_week_by_date(
        self,
        filename: str,
        date_str: str ) -> int:
        """
        Elimina la semana completa (lunes a domingo) correspondiente a `date_str`,
        asumiendo que el CSV tiene una columna `semana_año` en formato 'YYYY-WW'
        (semana ISO, que parte en lunes).

        Ejemplo:
            date_str = '2025-12-01' -> semana ISO (year, week) -> '2025-49'
            Se eliminan todas las filas donde semana_año == '2025-49'.
        """
        column_name: str = "semana_año"
        try:
            d = datetime.fromisoformat(date_str).date()
        except ValueError:
            raise ValueError(f"Fecha inválida: {date_str}. Se espera formato YYYY-MM-DD")

        iso = d.isocalendar()  # (year, week, weekday)
        year = iso.year
        week = iso.week
        semana_año = f"{year}-{week:02d}"

        # Reutilizamos el método anterior
        return self.remove_week_from_file(
            filename=filename,
            semana_año=semana_año,
        )

    def list_files(self):
        return self.s3_client.list_objects_v2(Bucket=self.s3_bucket)

# Global storage manager instance using centralized settings
storage_manager = StorageManager(
    env=settings.env,
    s3_bucket=settings.s3_files_bucket
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

