"""
Version manager for models
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional, List, Dict
import logging
from pathlib import Path

from app.utils.storage import StorageManager

load_dotenv()

logger = logging.getLogger(__name__)

class VersionManager(StorageManager):
    def __init__(self, env: Optional[str] = "local", s3_bucket: Optional[str] = None):
        # Set base directory for version management files
        self.base_dir = "models"
        self.filename = f"{self.base_dir}/version_manager.json"
        super().__init__(env, s3_bucket)
        self.create_version_manager()

    def save_model(self, model, metadata) -> None:
        """
        Save a model to storage using joblib.
        
        Best practices:
        - Local: Direct file write with joblib.dump
        - S3: Serialize to BytesIO buffer, then upload
        
        Args:
            model: Model object (Prophet, sklearn, etc.) to save
            metadata: Metadata dictionary to save with the model
        """
        import joblib
        from io import BytesIO
        
        version = metadata.get("version")
        complexity = metadata.get("complexity")
        model_path = f"models/{complexity}/{version}/model.pkl"
        metadata_path = f"models/{complexity}/{version}/metadata.json"

        if self.env == "local":
            # Local mode: Direct file write
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
            
            # Save model using joblib with compression
            joblib.dump(model, model_path, compress=3)
            
            # Save metadata as JSON
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Model saved locally: {model_path}")
            return

        # S3 mode: Serialize to BytesIO buffer first
        with BytesIO() as model_buffer:
            joblib.dump(model, model_buffer, compress=3)
            model_buffer.seek(0)
            self.s3_client.upload_fileobj(
                model_buffer,
                Bucket=self.s3_bucket,
                Key=model_path
            )
        
        # Save metadata to S3
        self.s3_client.put_object(
            Bucket=self.s3_bucket,
            Key=metadata_path,
            Body=json.dumps(metadata, indent=2)
        )
        logger.info(f"Model saved to S3: s3://{self.s3_bucket}/{model_path}")
    
    def load_model(self, complexity: str, version: str):
        """
        Load a model from storage using joblib.
        
        Best practices:
        - Local: Direct file read with joblib.load
        - S3: Download to BytesIO buffer, then load
        
        Args:
            complexity: Model complexity
            version: Version identifier
            
        Returns:
            Loaded model object
        """
        import joblib
        from io import BytesIO
        
        model_path = f"models/{complexity}/{version}/model.pkl"
        
        if self.env == "local":
            # Local mode: Direct file read
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model not found: {model_path}")
            
            model = joblib.load(model_path)
            logger.info(f"Model loaded from local: {model_path}")
            return model
        
        # S3 mode: Download to BytesIO buffer
        try:
            with BytesIO() as model_buffer:
                self.s3_client.download_fileobj(
                    Bucket=self.s3_bucket,
                    Key=model_path,
                    Fileobj=model_buffer
                )
                model_buffer.seek(0)
                model = joblib.load(model_buffer)
            
            logger.info(f"Model loaded from S3: s3://{self.s3_bucket}/{model_path}")
            return model
        except self.s3_client.exceptions.NoSuchKey:
            raise FileNotFoundError(f"Model not found in S3: s3://{self.s3_bucket}/{model_path}")

    
    def create_version_manager(self):
        """Create version manager configuration file if it doesn't exist."""
        if self.exists(self.filename):
            logger.info(f"Version manager file already exists: {self.filename}")
            return
            
        logger.info(f"Creating version manager file: {self.filename}")
        
        data = {
            "Alta": {
                "version": "",
                "activated_at": "",
                "activated_by": ""
            },
            "Media": {
                "version": "",
                "activated_at": "",
                "activated_by": ""
            },
            "Baja": {
                "version": "",
                "activated_at": "",
                "activated_by": ""
            },
            "Neonatología": {
                "version": "",
                "activated_at": "",
                "activated_by": ""
            },
            "Pediatría": {
                "version": "",
                "activated_at": "",
                "activated_by": ""
            }
        }

        if self.env == "local":
            # Create directory only if filename has a directory component
            dir_path = os.path.dirname(self.filename)
            if dir_path:  # Only create if there's actually a directory
                os.makedirs(dir_path, exist_ok=True)
            
            with open(self.filename, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Version manager file created locally: {self.filename}")
            return

        self.s3_client.put_object(Bucket=self.s3_bucket, Key=self.filename, Body=json.dumps(data))
        logger.info(f"Version manager file created in S3: {self.filename}")

    def get_version_manager(self):
        if self.env == "local":
            with open(self.filename, 'rb') as f:
                return json.load(f)
        obj = self.s3_client.get_object(Bucket=self.s3_bucket, Key=self.filename)
        return json.loads(obj['Body'].read())

    def get_active_version_data(self, complexity: str):
        versions = self.get_version_manager()
        return versions.get(complexity, {})

    def get_active_model(self, complexity: str):
        """
        Get the currently active model for a complexity.
        
        If no active version is set, defaults to the latest version.
        
        Args:
            complexity: Model complexity
            
        Returns:
            Loaded active model object
            
        Raises:
            ValueError: If no versions exist for the complexity
            FileNotFoundError: If the model file doesn't exist
        """
        active_data = self.get_active_version_data(complexity)
        version = active_data.get("version")
        
        # If no active version, get the latest one
        if not version:
            logger.info(f"No active version set for {complexity}, using latest version")
            versions = self.get_complexity_versions(complexity)
            
            if not versions:
                raise ValueError(f"No versions available for complexity: {complexity}")
            
            # Sort by version (assuming format: v_YYYY-MM-DD_HH-MM-SS or similar)
            # Get the last one (most recent)
            sorted_versions = sorted(versions, key=lambda x: x.get("version", ""), reverse=True)
            version = sorted_versions[0].get("version")
            
            if not version:
                raise ValueError(f"Could not determine latest version for complexity: {complexity}")
            
            logger.info(f"Using latest version for {complexity}: {version}")
        else:
            logger.info(f"Loading active model for {complexity}: {version}")
        
        return self.load_model(complexity, version)

    def set_active_version(self, complexity: str, version: str, user: str = "system"):
        versions = self.get_version_manager()
        versions[complexity] = {
            "version": version,
            "activated_at": datetime.now().isoformat(),
            "activated_by": user
        }
        if self.env == "local":
            with open(self.filename, 'w') as f:
                json.dump(versions, f, indent=2)
            return versions[complexity]
        self.s3_client.put_object(Bucket=self.s3_bucket, Key=self.filename, Body=json.dumps(versions))
        return versions[complexity]

    def set_active_versions_batch(self, versions_dict: Dict[str, str], user: str = "system"):
        """
        Set multiple active versions at once.
        
        Args:
            versions_dict: Dictionary mapping complexity to version
            user: User making the change
        """
        versions = self.get_version_manager()
        timestamp = datetime.now().isoformat()
        
        for complexity, version in versions_dict.items():
            if complexity in versions:
                versions[complexity] = {
                    "version": version,
                    "activated_at": timestamp,
                    "activated_by": user
                }
        
        if self.env == "local":
            with open(self.filename, 'w') as f:
                json.dump(versions, f, indent=2)
            return versions
        self.s3_client.put_object(Bucket=self.s3_bucket, Key=self.filename, Body=json.dumps(versions))
        return versions
        
    def get_complexity_versions(self, complexity: str):
        """Get all versions for a specific complexity."""
        if self.env == "local":
            # List local files
            complexity_dir = f"models/{complexity}"
            if not os.path.exists(complexity_dir):
                return []
            
            versions = []
            try:
                # Walk through version directories
                for version_dir in os.listdir(complexity_dir):
                    metadata_path = os.path.join(complexity_dir, version_dir, "metadata.json")
                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r') as f:
                            versions.append(json.load(f))
                return versions
            except Exception as e:
                logger.error(f"Error getting local complexity versions: {e}")
                return []
        
        # S3 mode
        s3_key = f"models/{complexity}"
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.s3_bucket, Prefix=s3_key)
            if 'Contents' not in response:
                return []
            
            versions = []
            for obj in response['Contents']:
                if obj['Key'].endswith("metadata.json"):
                    metadata = self.s3_client.get_object(Bucket=self.s3_bucket, Key=obj['Key'])
                    versions.append(json.loads(metadata['Body'].read()))
            return versions
        except self.s3_client.exceptions.NoSuchKey:
            return []
        except Exception as e:
            logger.error(f"Error getting S3 complexity versions: {e}")
            return []

    def get_version_metadata(self, complexity: str, version: str) -> Optional[Dict]:
        """
        Get metadata for a specific version.
        
        Args:
            complexity: Model complexity
            version: Version identifier
            
        Returns:
            Metadata dictionary or None if not found
        """
        metadata_path = f"models/{complexity}/{version}/metadata.json"
        try:
            if self.env == "local":
                if not os.path.exists(metadata_path):
                    return None
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            
            # S3 mode
            metadata = self.s3_client.get_object(Bucket=self.s3_bucket, Key=metadata_path)
            return json.loads(metadata['Body'].read())
        except FileNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Error getting version metadata: {e}")
            return None

    def compare_versions(self, complexity: str, versions: List[str]) -> List[Dict]:
        """
        Compare metrics between multiple versions.
        
        Args:
            complexity: Model complexity
            versions: List of version identifiers
            
        Returns:
            List of version metadata for comparison
        """
        comparison = []
        for version in versions:
            metadata = self.get_version_metadata(complexity, version)
            if metadata:
                comparison.append(metadata)
        return comparison

    def get_versions(self):
        complexities = {
            "Baja": [], "Media": [], "Alta": [], "Neonatología": [], "Pediatría": []
        }
        for complexity in complexities.keys():
            complexity_versions = self.get_complexity_versions(complexity)
            complexities[complexity] = complexity_versions
        return complexities

    def get_stats(self) -> Dict:
        """
        Get statistics about the model versioning system.
        
        Returns:
            Dictionary with system statistics
        """
        all_versions = self.get_versions()
        active_config = self.get_version_manager()
        
        total_versions = sum(len(versions) for versions in all_versions.values())
        versions_by_complexity = {k: len(v) for k, v in all_versions.items()}
        active_versions = {k: v.get("version", "") for k, v in active_config.items()}
        
        return {
            "total_versions": total_versions,
            "versions_by_complexity": versions_by_complexity,
            "active_versions": active_versions,
            "complexities": list(all_versions.keys())
        }




_s3_bucket = os.getenv("S3_DATA_BUCKET", None)
_env = os.getenv("ENV", "local")

version_manager = VersionManager(
    env=_env,
    s3_bucket=_s3_bucket
)