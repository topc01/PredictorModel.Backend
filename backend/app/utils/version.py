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










_s3_bucket = os.getenv("S3_DATA_BUCKET", None)

version_manager = VersionManager(
    s3_bucket=_s3_bucket
)