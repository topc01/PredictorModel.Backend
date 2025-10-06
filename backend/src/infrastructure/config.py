from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # JWT Settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    
    # Database Settings
    database_url: Optional[str] = None
    
    # CORS Settings
    cors_origins: list[str] = [
        "http://localhost:5173",
        "https://main.d12abg5dtejald.amplifyapp.com/",
        "https://develop.d12abg5dtejald.amplifyapp.com/",
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
