"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.auth import get_current_user
from app.models.user import UserRole
from app.core.auth0_client import auth0_client

router = APIRouter(tags=["auth"])


class UserInfoResponse(BaseModel):
    """User information response."""
    email: str
    name: str
    role: str
    auth0_user_id: str


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """Get current authenticated user information from Auth0."""
    email = current_user["email"]
    auth0_user_id = current_user["auth0_user_id"]
    name = current_user["name"]
    
    # Get user data from Auth0 Management API
    role = UserRole.VIEWER  # Default role
    try:
        auth0_user = auth0_client.get_user_by_email(email)
        if auth0_user:
            # Use name from Auth0 if available
            if auth0_user.get("name"):
                name = auth0_user.get("name")
            
            # Get role from Auth0 metadata
            role_str = auth0_client.get_user_role(email)
            if role_str:
                role = UserRole.ADMIN if role_str == "admin" else UserRole.VIEWER
    except Exception as e:
        print(f"Error getting user from Auth0 Management API: {e}")
        # Use defaults on error
    
    return UserInfoResponse(
        email=email,
        name=name,
        role=role.value,
        auth0_user_id=auth0_user_id
    )


@router.post("/sync")
async def sync_user(
    current_user: dict = Depends(get_current_user)
):
    """Get current user information from Auth0 (no longer syncs to Redis)."""
    email = current_user["email"]
    auth0_user_id = current_user["auth0_user_id"]
    name = current_user["name"]
    
    # Get role from Auth0
    role = UserRole.VIEWER
    try:
        role_str = auth0_client.get_user_role(email)
        if role_str:
            role = UserRole.ADMIN if role_str == "admin" else UserRole.VIEWER
        
        # Get updated name from Auth0 if available
        auth0_user = auth0_client.get_user_by_email(email)
        if auth0_user and auth0_user.get("name"):
            name = auth0_user.get("name")
    except Exception as e:
        print(f"Error getting user from Auth0: {e}")
    
    return {
        "message": "User information retrieved from Auth0",
        "user": {
            "email": email,
            "name": name,
            "role": role.value,
            "auth0_user_id": auth0_user_id
        }
    }

