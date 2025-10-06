from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from uuid import UUID

from ..controllers import AuthController
from ..middleware import get_current_user_id
from ...application.dtos import LoginRequest, RefreshTokenRequest, UserResponse, TokenResponse
from ...infrastructure.database import Database

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def get_auth_controller() -> AuthController:
    from ...infrastructure.database import Database
    from ...infrastructure.config import settings
    
    if not settings.database_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database not configured"
        )
    
    db = Database(settings.database_url)
    return AuthController(db)


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def login(
    request: LoginRequest,
    controller: Annotated[AuthController, Depends(get_auth_controller)]
) -> TokenResponse:
    return controller.login(request)


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    request: RefreshTokenRequest,
    controller: Annotated[AuthController, Depends(get_auth_controller)]
) -> dict:
    return controller.logout(request)


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
def refresh_token(
    request: RefreshTokenRequest,
    controller: Annotated[AuthController, Depends(get_auth_controller)]
) -> TokenResponse:
    return controller.refresh_token(request)


@router.get("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
def get_current_user(
    controller: Annotated[AuthController, Depends(get_auth_controller)],
    user_id: Annotated[UUID, Depends(get_current_user_id)]
) -> UserResponse:
    return controller.get_current_user(user_id)
