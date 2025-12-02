"""
Core configuration settings using Pydantic.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # App
    app_name: str = "Predictor Model Backend"
    app_version: str = "0.1.0"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    
    # CORS
    cors_origins: List[str] = [
        "http://localhost:5173",
        "https://main.d12abg5dtejald.amplifyapp.com",
        "https://develop.d12abg5dtejald.amplifyapp.com",
    ]
    
    # AWS (optional)
    aws_region: str = "us-east-1"
    s3_files_bucket: str = ""
    s3_data_bucket: str = ""
    
    # Auth0
    auth0_domain: str = ""
    auth0_api_audience: str = ""
    auth0_algorithms: str = "RS256"  # Comma-separated or single algorithm
    auth0_management_client_id: str = ""
    auth0_management_client_secret: str = ""
    auth0_management_domain: str = ""
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()

