"""User management routes using Redis."""
from fastapi import APIRouter, HTTPException, status
from typing import List

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse

router = APIRouter(tags=["users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate):
    """Create a new user."""
    try:
        user = User.create(
            email=user_data.email,
            name=user_data.name,
            role=user_data.role
        )
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{email}", response_model=UserResponse)
async def get_user(email: str):
    """Get a user by email."""
    user = User.get(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@router.get("/", response_model=List[UserResponse])
async def list_users(skip: int = 0, limit: int = 100):
    """List all users."""
    users = User.list_all(skip=skip, limit=limit)
    return users


@router.put("/{email}", response_model=UserResponse)
async def update_user(email: str, user_update: UserUpdate):
    """Update a user."""
    user = User.get(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.update(
        name=user_update.name,
        role=user_update.role
    )
    
    return user


@router.delete("/{email}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(email: str):
    """Delete a user."""
    user = User.get(email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.delete()
    return None
