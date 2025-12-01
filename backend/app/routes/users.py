"""User management routes using Auth0."""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from pydantic import BaseModel, EmailStr

from app.models.user import UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.core.auth import require_role, get_current_user
from app.core.auth0_client import auth0_client

import logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["users"])


class UserInviteRequest(BaseModel):
    """Request to invite a new user."""
    email: EmailStr
    name: str
    role: UserRole = UserRole.VIEWER
    password: str


@router.post("/invite", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    invite_data: UserInviteRequest,
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """Invite a new user (creates in Auth0 and Redis)."""
    try:
        # Check if user already exists in Redis
        existing_user = auth0_client.get_user_by_email(invite_data.email)
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"User with email {invite_data.email} already exists")
        
        # Create user in Auth0
        auth0_user_data = auth0_client.create_user(
            email=invite_data.email,
            name=invite_data.name,
            password=invite_data.password,
            role=invite_data.role.value
        )
        
        return UserResponse(
          email=auth0_user_data["email"],
          name=auth0_user_data["name"],
          role=auth0_user_data["app_metadata"]["role"],
          created_at=auth0_user_data["created_at"],
          updated_at=auth0_user_data["updated_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error creating user: {str(e)}"
        )


@router.get("/{email}", response_model=UserResponse)
async def get_user(
    email: str,
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """Get a user by email."""
    user = auth0_client.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
          email=user["email"],
          name=user["name"],
          role=user.get("app_metadata", {}).get("role"),
          created_at=user.get("created_at"),
          updated_at=user.get("updated_at")
        )


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """List all users."""
    users = auth0_client.get_all_users(skip=skip, limit=limit)
    return [UserResponse(
          email=user["email"],
          name=user["name"],
          role=user.get("app_metadata", {}).get("role"),
          created_at=user.get("created_at"),
          updated_at=user.get("updated_at")
        ) for user in users]


@router.put("/{email}", response_model=UserResponse)
async def update_user(
    email: str,
    user_update: UserUpdate,
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """Update a user."""
    user = auth0_client.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Update in Auth0 if auth0_user_id exists
    if user_update.role:
        try:
            auth0_client.update_user_role(
                user_id=user_id,
                role=user_update.role.value
            )
        except Exception as e:
            # Log error but don't fail the request
            logger.error(f"Error updating Auth0 user role: {e}")
    
    return UserResponse(
          email=user["email"],
          name=user["name"],
          role=user.get("app_metadata", {}).get("role"),
          created_at=user.get("created_at"),
          updated_at=user.get("updated_at")
        )


@router.delete("/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    email: str,
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """Delete a user."""
    user = auth0_client.get_user_by_email(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    user_id = user.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    
    # Delete from Auth0 if auth0_user_id exists
    try:
        auth0_client.delete_user(user_id)
    except Exception as e:
        # Log error but continue with Redis deletion
        logger.error(f"Error deleting Auth0 user: {e}")
    
   
    return None
