"""
Auth0 Management API client for user management operations.
"""

import httpx
from typing import Dict, List, Optional
from app.auth.config import auth0_settings
from app.auth.exceptions import AuthError


class Auth0ManagementAPI:
    """Client for Auth0 Management API operations."""
    
    def __init__(self):
        if not auth0_settings.validate_management_api_config():
            raise ValueError(
                "Auth0 Management API not properly configured. "
                "Set AUTH0_MANAGEMENT_API_DOMAIN, AUTH0_MANAGEMENT_API_CLIENT_ID, "
                "and AUTH0_MANAGEMENT_API_CLIENT_SECRET environment variables."
            )
        self.domain = auth0_settings.management_api_domain
        self.client_id = auth0_settings.management_api_client_id
        self.client_secret = auth0_settings.management_api_client_secret
        self._access_token: Optional[str] = None
    
    async def _get_access_token(self) -> str:
        """
        Get or refresh M2M access token for Management API.
        
        Returns:
            str: Access token
        """
        if self._access_token:
            return self._access_token
        
        token_url = f"https://{self.domain}/oauth/token"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                json={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "audience": f"https://{self.domain}/api/v2/",
                    "grant_type": "client_credentials",
                },
                timeout=10.0,
            )
            
            if response.status_code != 200:
                raise AuthError(f"Failed to get Management API token: {response.text}")
            
            data = response.json()
            self._access_token = data["access_token"]
            return self._access_token
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict:
        """
        Make authenticated request to Management API.
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (without base URL)
            json_data: JSON body for request
            params: Query parameters
            
        Returns:
            dict: Response data
        """
        token = await self._get_access_token()
        url = f"https://{self.domain}/api/v2/{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=30.0,
            )
            
            if response.status_code >= 400:
                error_detail = response.text
                try:
                    error_json = response.json()
                    error_detail = error_json.get("message", error_detail)
                except:
                    pass
                raise AuthError(f"Management API error: {error_detail}")
            
            if response.status_code == 204:  # No content
                return {}
            
            return response.json()
    
    async def create_user(
        self,
        email: str,
        password: Optional[str] = None,
        connection: str = "Username-Password-Authentication",
        user_metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Create a new user in Auth0.
        
        Args:
            email: User email
            password: User password (optional, for password-based connections)
            connection: Auth0 connection name
            user_metadata: Additional user metadata
            
        Returns:
            dict: Created user data
        """
        user_data = {
            "email": email,
            "connection": connection,
            "email_verified": False,
        }
        
        if password:
            user_data["password"] = password
        
        if user_metadata:
            user_data["user_metadata"] = user_metadata
        
        return await self._make_request("POST", "users", json_data=user_data)
    
    async def invite_user(
        self,
        email: str,
        connection: str = "Username-Password-Authentication",
        client_id: Optional[str] = None,
    ) -> Dict:
        """
        Send an invitation to a user via email.
        
        Args:
            email: User email
            connection: Auth0 connection name
            client_id: Client ID for invitation link (optional, uses first client if not provided)
            
        Returns:
            dict: Invitation data with ticket URL
        """
        invite_data = {
            "email": email,
            "connection": connection,
        }
        
        if client_id:
            invite_data["client_id"] = client_id
        
        return await self._make_request("POST", "tickets", json_data=invite_data)
    
    async def list_users(
        self,
        page: int = 0,
        per_page: int = 50,
        search_engine: str = "v3",
    ) -> Dict:
        """
        List users in Auth0.
        
        Args:
            page: Page number (0-indexed)
            per_page: Number of users per page
            search_engine: Search engine version
            
        Returns:
            dict: Users list with pagination info
        """
        params = {
            "page": page,
            "per_page": per_page,
            "search_engine": search_engine,
        }
        
        return await self._make_request("GET", "users", params=params)
    
    async def get_user(self, user_id: str) -> Dict:
        """
        Get user by ID.
        
        Args:
            user_id: Auth0 user ID
            
        Returns:
            dict: User data
        """
        return await self._make_request("GET", f"users/{user_id}")
    
    async def update_user(
        self,
        user_id: str,
        user_data: Dict,
    ) -> Dict:
        """
        Update user information.
        
        Args:
            user_id: Auth0 user ID
            user_data: User data to update
            
        Returns:
            dict: Updated user data
        """
        return await self._make_request("PATCH", f"users/{user_id}", json_data=user_data)
    
    async def assign_roles(self, user_id: str, roles: List[str]) -> Dict:
        """
        Assign roles to a user.
        
        Args:
            user_id: Auth0 user ID
            roles: List of role IDs to assign
            
        Returns:
            dict: Response data
        """
        return await self._make_request(
            "POST",
            f"users/{user_id}/roles",
            json_data={"roles": roles},
        )
    
    async def remove_roles(self, user_id: str, roles: List[str]) -> Dict:
        """
        Remove roles from a user.
        
        Args:
            user_id: Auth0 user ID
            roles: List of role IDs to remove
            
        Returns:
            dict: Response data
        """
        return await self._make_request(
            "DELETE",
            f"users/{user_id}/roles",
            json_data={"roles": roles},
        )
    
    async def get_user_roles(self, user_id: str) -> List[Dict]:
        """
        Get roles assigned to a user.
        
        Args:
            user_id: Auth0 user ID
            
        Returns:
            List[dict]: List of role objects
        """
        return await self._make_request("GET", f"users/{user_id}/roles")
    
    async def list_roles(self) -> List[Dict]:
        """
        List all roles in Auth0.
        
        Returns:
            List[dict]: List of role objects
        """
        return await self._make_request("GET", "roles")
    
    async def delete_user(self, user_id: str) -> None:
        """
        Delete a user from Auth0.
        
        Args:
            user_id: Auth0 user ID
        """
        await self._make_request("DELETE", f"users/{user_id}")


# Global instance
management_api = Auth0ManagementAPI()

