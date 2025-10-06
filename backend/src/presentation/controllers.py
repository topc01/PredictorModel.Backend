from fastapi import HTTPException, status, Depends
from typing import Annotated
from uuid import UUID

from ..application.dtos import LoginRequest, RefreshTokenRequest, UserResponse, TokenResponse
from ..application.use_cases import LoginUseCase, LogoutUseCase, RefreshTokenUseCase, GetCurrentUserUseCase
from ..infrastructure.repositories import SQLUserRepository, SQLRefreshTokenRepository
from ..infrastructure.services import BcryptPasswordService, JWTTokenService
from ..infrastructure.database import Database
from .middleware import get_current_user_id


class AuthController:
    def __init__(self, db: Database):
        self._db = db
        self._password_service = BcryptPasswordService()
        self._token_service = JWTTokenService()
        
        self._user_repository = SQLUserRepository(db.get_session())
        self._refresh_token_repository = SQLRefreshTokenRepository(db.get_session())
        
        self._login_use_case = LoginUseCase(
            self._user_repository,
            self._refresh_token_repository,
            self._password_service,
            self._token_service
        )
        
        self._logout_use_case = LogoutUseCase(self._refresh_token_repository)
        
        self._refresh_token_use_case = RefreshTokenUseCase(
            self._user_repository,
            self._refresh_token_repository,
            self._token_service
        )
        
        self._get_current_user_use_case = GetCurrentUserUseCase(self._user_repository)

    def login(self, request: LoginRequest) -> TokenResponse:
        try:
            return self._login_use_case.execute(request)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    def logout(self, request: RefreshTokenRequest) -> dict:
        try:
            success = self._logout_use_case.execute(request.refresh_token)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid refresh token"
                )
            return {"message": "Successfully logged out"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    def refresh_token(self, request: RefreshTokenRequest) -> TokenResponse:
        try:
            return self._refresh_token_use_case.execute(request)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    def get_current_user(self, user_id: Annotated[UUID, Depends(get_current_user_id)]) -> UserResponse:
        try:
            return self._get_current_user_use_case.execute(user_id)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
