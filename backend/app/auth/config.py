"""
Auth0 configuration settings.
"""

import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Auth0Settings:
    """Auth0 configuration settings loaded from environment variables."""
    
    def __init__(self):
        self.domain: str = os.getenv("AUTH0_DOMAIN", "")
        self.api_audience: str = os.getenv("AUTH0_API_AUDIENCE", "")
        self.issuer: str = os.getenv("AUTH0_ISSUER", "")
        self.algorithms: List[str] = os.getenv("AUTH0_ALGORITHMS", "RS256").split(",")
        
        # Management API settings
        self.management_api_domain: str = os.getenv("AUTH0_MANAGEMENT_API_DOMAIN", "")
        self.management_api_client_id: str = os.getenv("AUTH0_MANAGEMENT_API_CLIENT_ID", "")
        self.management_api_client_secret: str = os.getenv("AUTH0_MANAGEMENT_API_CLIENT_SECRET", "")
        
        # Validate required settings
        if not self.domain:
            raise ValueError("AUTH0_DOMAIN environment variable is required")
        if not self.api_audience:
            raise ValueError("AUTH0_API_AUDIENCE environment variable is required")
        if not self.issuer:
            # Default to domain if issuer not set
            self.issuer = f"https://{self.domain}/"
        
        # JWKS URL for token verification
        self.jwks_url: str = f"https://{self.domain}/.well-known/jwks.json"
        
        # Management API URL
        if self.management_api_domain:
            self.management_api_url: str = f"https://{self.management_api_domain}/api/v2"
        else:
            self.management_api_url: str = f"https://{self.domain}/api/v2"
    
    def validate_management_api_config(self) -> bool:
        """Check if Management API is properly configured."""
        return all([
            self.management_api_domain,
            self.management_api_client_id,
            self.management_api_client_secret,
        ])


# Global settings instance
auth0_settings = Auth0Settings()

