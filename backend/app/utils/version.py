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
import joblib

from app.utils.storage import StorageManager
from app.utils.complexities import ComplexityMapper

load_dotenv()

logger = logging.getLogger(__name__)

# Backward compatibility: keep the old label() function
def label(complexity: str) -> str:
    """
    Convert complexity to label (backward compatibility).
    
    Deprecated: Use ComplexityMapper.to_label() instead.
    """
    try:
        return ComplexityMapper.to_label(complexity)
    except ValueError:
        # If not found, return as-is for backward compatibility
        return complexity


class VersionManager(StorageManager):
    """
Version manager for models

s3://tu-bucket/models/  
├── Alta/
│   ├── v1_2024-11-26_18-30-00/
│   │   ├── model.pkl
│   │   └── metadata.json
│   ├── v2_2024-11-27_10-15-00/
│   │   ├── model.pkl
│   │   └── metadata.json
│   └── v3_2024-11-28_14-45-00/
│       ├── model.pkl
│       └── metadata.json
├── Baja/
│   ├── v1_2024-11-26_18-30-00/
│   │   ├── model.pkl
│   │   └── metadata.json
│   └── v2_2024-11-27_10-15-00/
│       ├── model.pkl
│       └── metadata.json
├── Media/
│   └── ...
├── Neonatología/
│   └── ...
├── Pediatría/
│   └── ...
├── (in progress) Inte. Pediátrico/ # TODO
│   └── ...
├── (in progress) Maternidad/ # TODO
│   └── ...
├── feature_names/
│   ├── v1_2024-11-26_18-30-00.pkl
│   └── v2_2024-11-27_10-15-00.pkl
└── active_versions.json 
    """

    # Get all valid complexity labels from the centralized mapper
    complexities = ComplexityMapper.get_all_labels()

    def __init__(self, env: Optional[str] = "local", s3_bucket: Optional[str] = None):
        # Set base directory for version management files
        self.base_dir = "models"
        self.filename = f"{self.base_dir}/active_versions.json"
        super().__init__(env, s3_bucket)

        class Path:
            base_dir = "models"
            _complexity = None
            _version = None
            def __call__(self_, complexity: str, version: Optional[str] = None):
                self_._complexity = complexity
                self_._version = version
                return self_
            @property
            def complexity(self_):
                if not self_._complexity:
                    raise ValueError("Complexity not set")
                return self_._complexity
            @property
            def version(self_):
                if not self_._version:
                    raise ValueError("Version not set")
                return self_._version
            @property
            def model(self_):
                return f"{self_.version_dir}/model.pkl"
            @property
            def metadata(self_):
                return f"{self_.version_dir}/metadata.json"
            @property
            def dir(self_):
                return f"{self_.base_dir}/{label(self_.complexity)}"
            @property
            def version_dir(self_):
                if not self_._version:
                    raise ValueError("Version not set - cannot access version_dir")
                return f"{self_.dir}/{self_.version}"
            @property
            def active_versions_register(self_):
                return f"{self_.base_dir}/active_versions.json"
            @property
            def base_model(self_):
                """Path to base model file (fallback when no versions exist)."""
                if not self_._complexity:
                    raise ValueError("Complexity not set")
                return f"{self_.base_dir}/{label(self_._complexity)}.pkl"
            @property
            def feature_names_file(self_):
                """Path to feature names file."""
                return f"{self_.base_dir}/feature_names.pkl"
            
            @property
            def base_metrics_file(self_):
                """Path to base metrics file (fallback when no versions exist)."""
                if not self_._complexity:
                    raise ValueError("Complexity not set")
                return f"{self_.base_dir}/results/{label(self_._complexity)}.json"

        

        self.path = Path()
        self._create_version_manager()

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
        model_path = self.path(complexity, version).model
        metadata_path = self.path(complexity, version).metadata

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

    def _load_model_path(self, model_path: str) -> "Model":
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
    
    def _load_model(self, complexity: str, version: str) -> "Model":
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
        from io import BytesIO
        
        model_path = self.path(complexity, version).model

        return self._load_model_path(model_path)
    
    def _create_version_manager(self) -> None:
        """Create version manager configuration file if it doesn't exist."""
        if self.exists(self.filename):
            logger.info(f"Version manager file already exists: {self.filename}")
            return
        manager_path = self.path.active_versions_register
        logger.info(f"Creating version manager file: {manager_path}")
        
        data = { complexity: { "version": "", "activated_at": "", "activated_by": "" } for complexity in self.complexities }
        self.data = data
        if self.env == "local":
            # Create directory only if filename has a directory component
            dir_path = os.path.dirname(manager_path)
            if dir_path:  # Only create if there's actually a directory
                os.makedirs(dir_path, exist_ok=True)
            
            with open(manager_path, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Version manager file created locally: {manager_path}")
            return

        self.s3_client.put_object(Bucket=self.s3_bucket, Key=manager_path, Body=json.dumps(data))
        logger.info(f"Version manager file created in S3: {manager_path}")

    @property
    def _active_versions(self) -> dict:
        if self.env == "local":
            with open(self.path.active_versions_register, 'rb') as f:
                return json.load(f)
        obj = self.s3_client.get_object(Bucket=self.s3_bucket, Key=self.path.active_versions_register)
        return json.loads(obj['Body'].read())

    def get_active_version_data(self, complexity: str) -> dict:
        """Method to get raw active version data from JSON."""
        return self._active_versions.get(complexity, {})

    def get_base_model(self, complexity: str) -> "Model":
        """
        Load the base model for a given complexity.
        
        This is used as a fallback when no versioned models exist.
        The base model is stored at: models/{complexity}.pkl
        
        Args:
            complexity: Model complexity
            
        Returns:
            Loaded base model object
        """
        base_model_path = self.path(complexity).base_model
        logger.info(f"Loading base model for {complexity} from: {base_model_path}")
        return self._load_model_path(base_model_path)
    
    def get_latest_version(self, complexity: str) -> Optional[str]:
        logger.info(f"Using latest version for {complexity}")
        versions = self.get_complexity_versions(complexity)
        if not versions:
            return None
        
        # Sort by version (assuming format: v_YYYY-MM-DD_HH-MM-SS)
        sorted_versions = sorted(versions, key=lambda x: x.get("version", ""), reverse=True)
        version = sorted_versions[0].get("version")
        return version

    def get_active_version(self, complexity: str) -> Optional[str]:
        """
        Get the active version for a complexity.
        
        If no active version is set in active_versions.json, returns the latest version.
        This is the main method to use for getting which version to use.
        
        Args:
            complexity: Model complexity
            
        Returns:
            Version string (e.g., "v_2025-11-28_17-18-28")
            
        Raises:
            ValueError: If no versions exist for the complexity
        """
        
        version = self._active_versions.get(complexity, {}).get("version")
        
        # If no active version set, get the latest one
        if not version:
            return self.get_latest_version(complexity)
            
        logger.info(f"Using active version for {complexity}: {version}")
        
        return version

    def get_model(self, complexity: str) -> "Model":
        """
        Load the model for a complexity.
        
        Uses get_active_version() to determine which version to load,
        then loads that model.
        
        Args:
            complexity: Model complexity
            
        Returns:
            Loaded model object
        """
        version = self.get_active_version(complexity)
        if not version:
            return self.get_base_model(complexity)
        return self._load_model(complexity, version)

    def set_active_version(self, complexity: str, version: str, user: str = "system") -> None:
        active_versions = self._active_versions
        active_versions[complexity] = {
            "version": version,
            "activated_at": datetime.now().isoformat(),
            "activated_by": user
        }
        if self.env == "local":
            with open(self.filename, 'w') as f:
                json.dump(active_versions, f, indent=2)
            return
        self.s3_client.put_object(Bucket=self.s3_bucket, Key=self.filename, Body=json.dumps(active_versions))

    def set_active_versions_batch(self, versions_dict: Dict[str, str], user: str = "system") -> None:
        """
        Set multiple active versions at once.
        
        Args:
            versions_dict: Dictionary mapping complexity to version
            user: User making the change
        """
        active_versions = self._active_versions
        timestamp = datetime.now().isoformat()
        
        for complexity, version in versions_dict.items():
            if complexity in active_versions:
                active_versions[complexity] = {
                    "version": version,
                    "activated_at": timestamp,
                    "activated_by": user
                }
        
        if self.env == "local":
            with open(self.filename, 'w') as f:
                json.dump(active_versions, f, indent=2)
            return  
        self.s3_client.put_object(Bucket=self.s3_bucket, Key=self.filename, Body=json.dumps(active_versions))
        
    def get_complexity_versions(self, complexity: str) -> list[dict]:
        """Get all versions for a specific complexity."""
        if self.env == "local":
            # List local files
            complexity_dir = self.path(complexity).dir
            if not os.path.exists(complexity_dir):
                logger.warning(f"No versions found for complexity: {complexity_dir}")
                return []
            
            versions = []
            try:
                # Walk through version directories
                for version_dir in os.listdir(complexity_dir):
                    metadata_path = self.path(complexity, version_dir).metadata
                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r') as f:
                            versions.append(json.load(f))
                return versions
            except Exception as e:
                logger.error(f"Error getting local complexity versions: {e}")
                return []
        
        # S3 mode
        s3_key = self.path(complexity).dir
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
        metadata_path = self.path(complexity, version).metadata
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

    def get_versions(self):
        complexities = { complexity: [] for complexity in self.complexities }
        for complexity in complexities.keys():
            complexity_versions = self.get_complexity_versions(complexity)
            complexities[complexity] = complexity_versions
        return complexities

    def get_active_versions(self):
        return { complexity: self.get_active_version(complexity) for complexity in self.complexities }

    def get_feature_names(self):
        """
        Load feature names from storage.
        
        Returns:
            List of feature names
        """
        feature_names_path = self.path().feature_names_file
        logger.info(f"Loading feature names from: {feature_names_path}")
        
        if self.env == "local":
            if not os.path.exists(feature_names_path):
                raise FileNotFoundError(f"Feature names file not found: {feature_names_path}")
            return joblib.load(feature_names_path)
        
        # S3 mode
        from io import BytesIO
        try:
            with BytesIO() as buffer:
                self.s3_client.download_fileobj(
                    Bucket=self.s3_bucket,
                    Key=feature_names_path,
                    Fileobj=buffer
                )
                buffer.seek(0)
                return joblib.load(buffer)
        except self.s3_client.exceptions.NoSuchKey:
            raise FileNotFoundError(f"Feature names not found in S3: s3://{self.s3_bucket}/{feature_names_path}")



_s3_bucket = os.getenv("S3_DATA_BUCKET", None)
_env = os.getenv("ENV", "local")

version_manager = VersionManager(
    env=_env,
    s3_bucket=_s3_bucket
)