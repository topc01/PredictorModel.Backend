"""
Version manager for models
"""

import os
from dotenv import load_dotenv
from typing import Optional

from app.utils.storage import StorageManager

load_dotenv()

class VersionManager(StorageManager):
    def __init__(self, s3_bucket: Optional[str] = None):
        self.filename = "version_manager.json"
        super().__init__(s3_bucket)

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

        self.s3_client.put_object(Bucket=self.s3_bucket, Key=self.filename, Body=json.dumps(data))

    def get_version_manager(self):
        obj = self.s3_client.get_object(Bucket=self.s3_bucket, Key=self.filename)
        return json.loads(obj['Body'].read())

    def get_active_version_data(self, complexity: str):
        versions = self.get_version_manager()
        return versions.get(complexity, {})

    def set_active_version(self, complexity: str, version: str):
        versions = self.get_version_manager()
        versions[complexity] = {
            "version": version,
            "activated_at": datetime.now().isoformat(),
            "activated_by": "" # TODO: get user from request
        }
        self.s3_client.put_object(Bucket=self.s3_bucket, Key=self.filename, Body=json.dumps(versions))

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
        
    def get_complexity_versions(self, complexity: str):
        s3_key = f"models/{complexity}"
        try:
            response = self.s3_client.list_objects_v2(Bucket=self.s3_bucket, Prefix=s3_key)
            versions = []
            for obj in response['Contents']:
                if obj['Key'].endswith("metadata.json"):
                    metadata = self.s3_client.get_object(Bucket=self.s3_bucket, Key=obj['Key'])
                    versions.append(json.loads(metadata['Body'].read()))
            return versions
        except self.s3_client.exceptions.NoSuchKey:
            return None

    def get_versions(self):
        complexities = {
            "Baja": [], "Media": [], "Alta": [], "Neonatología": [], "Pediatría": []
        }
        for complexity in complexities.keys():
            complexity_versions = self.get_complexity_versions(complexity)
            complexities[complexity] = complexity_versions
        return complexities 






_s3_bucket = os.getenv("S3_DATA_BUCKET", None)

version_manager = VersionManager(
    s3_bucket=_s3_bucket
)