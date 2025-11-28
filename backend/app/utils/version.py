"""
Version manager for models
"""

import os
import json
from datetime import datetime
from dotenv import load_dotenv
from typing import Optional, List, Dict

from app.utils.storage import StorageManager

load_dotenv()

class VersionManager(StorageManager):
    def __init__(self, env: Optional[str] = "local", s3_bucket: Optional[str] = None):
        self.filename = "version_manager.json"
        super().__init__(env, s3_bucket)

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

        if self.env == "local":
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
            with open(model_path, 'wb') as f:
                f.write(model)
            with open(metadata_path, 'wb') as f:
                f.write(json.dumps(metadata))
            return

        self.s3_client.put_object(Bucket=self.s3_bucket, Key=model_path, Body=model)
        self.s3_client.put_object(Bucket=self.s3_bucket, Key=metadata_path, Body=json.dumps(metadata))
    
    def create_version_manager(self):
        if self.exists(self.filename):
            return
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
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            with open(self.filename, 'wb') as f:
                f.write(json.dumps(data))
            return

        self.s3_client.put_object(Bucket=self.s3_bucket, Key=self.filename, Body=json.dumps(data))

    def get_version_manager(self):
        if self.env == "local":
            with open(self.filename, 'rb') as f:
                return json.load(f)
        obj = self.s3_client.get_object(Bucket=self.s3_bucket, Key=self.filename)
        return json.loads(obj['Body'].read())

    def get_active_version_data(self, complexity: str):
        versions = self.get_version_manager()
        return versions.get(complexity, {})

    def set_active_version(self, complexity: str, version: str, user: str = "system"):
        versions = self.get_version_manager()
        versions[complexity] = {
            "version": version,
            "activated_at": datetime.now().isoformat(),
            "activated_by": user
        }
        if self.env == "local":
            with open(self.filename, 'wb') as f:
                f.write(json.dumps(versions))
            return
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
            with open(self.filename, 'wb') as f:
                f.write(json.dumps(versions))
            return
        self.s3_client.put_object(Bucket=self.s3_bucket, Key=self.filename, Body=json.dumps(versions))
        return versions
        
    def get_complexity_versions(self, complexity: str):
        s3_key = f"models/{complexity}"
        try:
            if self.env == "local":
                response = self.s3_client.list_objects_v2(Bucket=self.s3_bucket, Prefix=s3_key)
                if 'Contents' not in response:
                    return []
                
                versions = []
                for obj in response['Contents']:
                    if obj['Key'].endswith("metadata.json"):
                        metadata = self.s3_client.get_object(Bucket=self.s3_bucket, Key=obj['Key'])
                        versions.append(json.loads(metadata['Body'].read()))
                return versions
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
            print(f"Error getting complexity versions: {e}")
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
                with open(metadata_path, 'rb') as f:
                    return json.load(f)
            metadata = self.s3_client.get_object(Bucket=self.s3_bucket, Key=metadata_path)
            return json.loads(metadata['Body'].read())
        except self.s3_client.exceptions.NoSuchKey:
            return None
        except Exception as e:
            print(f"Error getting version metadata: {e}")
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