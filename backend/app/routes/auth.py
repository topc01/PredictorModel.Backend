"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.auth import get_current_user
from app.models.user import User, UserRole
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
    """Get current authenticated user information."""
    email = current_user["email"]
    auth0_user_id = current_user["auth0_user_id"]
    
    # Get user from Redis
    user = User.get(email)
    
    if not user:
        # Sync user from Auth0
        name = current_user["name"]
        role = UserRole.VIEWER  # Default role
        
        # Try to get role from Auth0 metadata
        try:
            auth0_user = auth0_client.get_user_by_email(email)
            if auth0_user:
                app_metadata = auth0_user.get("app_metadata", {})
                role_str = app_metadata.get("role", "viewer")
                role = UserRole.ADMIN if role_str == "admin" else UserRole.VIEWER
        except Exception:
            pass
        
        user = User.sync_from_auth0(
            auth0_user_id=auth0_user_id,
            email=email,
            name=name,
            role=role
        )
    
    return UserInfoResponse(
        email=user.email,
        name=user.name,
        role=user.role.value,
        auth0_user_id=user.auth0_user_id or auth0_user_id
    )


@router.post("/sync")
async def sync_user(
    current_user: dict = Depends(get_current_user)
):
    """Sync user from Auth0 to Redis."""
    email = current_user["email"]
    auth0_user_id = current_user["auth0_user_id"]
    name = current_user["name"]
    
    # Get role from Auth0
    role = UserRole.VIEWER
    try:
        auth0_user = auth0_client.get_user_by_email(email)
        if auth0_user:
            app_metadata = auth0_user.get("app_metadata", {})
            role_str = app_metadata.get("role", "viewer")
            role = UserRole.ADMIN if role_str == "admin" else UserRole.VIEWER
    except Exception:
        pass
    
    user = User.sync_from_auth0(
        auth0_user_id=auth0_user_id,
        email=email,
        name=name,
        role=role
    )
    
    return {
        "message": "User synced successfully",
        "user": {
            "email": user.email,
            "name": user.name,
            "role": user.role.value
        }
    }

