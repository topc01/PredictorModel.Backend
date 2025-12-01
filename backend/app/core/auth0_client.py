"""Auth0 Management API client."""
import httpx
from typing import Optional, Dict, Any
from app.core.config import settings


class Auth0ManagementClient:
    """Client for Auth0 Management API."""
    
    def __init__(self):
        self.domain = settings.auth0_management_domain or settings.auth0_domain
        self.client_id = settings.auth0_management_client_id
        self.client_secret = settings.auth0_management_client_secret
        self._access_token: Optional[str] = None
    
    def get_access_token(self) -> str:
        """Get access token for Management API."""
        if self._access_token:
            return self._access_token
        
        url = f"https://{self.domain}/oauth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": f"https://{self.domain}/api/v2/",
            "grant_type": "client_credentials"
        }
        
        response = httpx.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        self._access_token = data["access_token"]
        return self._access_token
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers with access token."""
        token = self.get_access_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def create_user(
        self,
        email: str,
        name: str,
        password: str,
        connection: str = "Username-Password-Authentication",
        role: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new user in Auth0."""
        url = f"https://{self.domain}/api/v2/users"
        payload = {
            "email": email,
            "name": name,
            "password": password,
            "connection": connection,
            "email_verified": False,
            "app_metadata": {
                "role": role or "viewer"
            }
        }
        
        response = httpx.post(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email from Auth0."""
        url = f"https://{self.domain}/api/v2/users-by-email"
        params = {"email": email}
        
        response = httpx.get(url, params=params, headers=self._get_headers())
        response.raise_for_status()
        users = response.json()
        
        if users:
            return users[0]
        return None
    
    def update_user_metadata(
        self,
        user_id: str,
        app_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user app_metadata in Auth0."""
        url = f"https://{self.domain}/api/v2/users/{user_id}"
        payload = {"app_metadata": app_metadata}
        
        response = httpx.patch(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()
    
    def update_user_role(self, user_id: str, role: str) -> Dict[str, Any]:
        """Update user role in app_metadata."""
        return self.update_user_metadata(user_id, {"role": role})
    
    def delete_user(self, user_id: str) -> None:
        """Delete user from Auth0."""
        url = f"https://{self.domain}/api/v2/users/{user_id}"
        response = httpx.delete(url, headers=self._get_headers())
        response.raise_for_status()
    
    def change_password(self, user_id: str, password: str) -> Dict[str, Any]:
        """Change user password."""
        url = f"https://{self.domain}/api/v2/users/{user_id}"
        payload = {"password": password}
        
        response = httpx.patch(url, json=payload, headers=self._get_headers())
        response.raise_for_status()
        return response.json()
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by Auth0 user ID."""
        url = f"https://{self.domain}/api/v2/users/{user_id}"
        
        response = httpx.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response.json()
    
    def get_user_role(self, email: str) -> Optional[str]:
        """Get user role from Auth0 app_metadata."""
        try:
            auth0_user = self.get_user_by_email(email)
            if auth0_user:
                # Check app_metadata first, then user_metadata as fallback
                app_metadata = auth0_user.get("app_metadata", {})
                user_metadata = auth0_user.get("user_metadata", {})
                
                # Try app_metadata first
                role = app_metadata.get("role")
                if not role:
                    # Fallback to user_metadata
                    role = user_metadata.get("role")
                
                return role.lower() if role else None
        except Exception as e:
            print(f"Error getting user role from Auth0: {e}")
            return None
        return None
    
    def get_user_role_by_id(self, user_id: str) -> Optional[str]:
        """Get user role from Auth0 app_metadata using user ID."""
        try:
            auth0_user = self.get_user_by_id(user_id)
            if auth0_user:
                # Check app_metadata first, then user_metadata as fallback
                app_metadata = auth0_user.get("app_metadata", {})
                user_metadata = auth0_user.get("user_metadata", {})
                
                # Try app_metadata first
                role = app_metadata.get("role")
                if not role:
                    # Fallback to user_metadata
                    role = user_metadata.get("role")
                
                return role.lower() if role else None
        except Exception as e:
            print(f"Error getting user role from Auth0: {e}")
            return None
        return None


# Global instance
auth0_client = Auth0ManagementClient()

