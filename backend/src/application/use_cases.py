from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from .dtos import LoginRequest, RefreshTokenRequest, UserResponse, TokenResponse
from ..domain.entities import User, RefreshToken
from ..domain.repositories import UserRepository, RefreshTokenRepository
from ..domain.services import PasswordService, TokenService


class LoginUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        password_service: PasswordService,
        token_service: TokenService,
    ):
        self._user_repository = user_repository
        self._refresh_token_repository = refresh_token_repository
        self._password_service = password_service
        self._token_service = token_service

    def execute(self, request: LoginRequest) -> TokenResponse:
        user = self._user_repository.get_by_email(request.email)
        
        if not user or not self._password_service.verify_password(request.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )

        token_pair = self._token_service.create_token_pair(user.id, user.email)
        
        refresh_token_entity = RefreshToken(
            user_id=user.id,
            token=token_pair.refresh_token,
            expires_at=self._get_refresh_token_expiry()
        )
        
        self._refresh_token_repository.create(refresh_token_entity)
        
        return TokenResponse(
            access_token=token_pair.access_token,
            refresh_token=token_pair.refresh_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in
        )

    def _get_refresh_token_expiry(self):
        from datetime import datetime, timedelta
        return datetime.utcnow() + timedelta(days=7)


class LogoutUseCase:
    def __init__(self, refresh_token_repository: RefreshTokenRepository):
        self._refresh_token_repository = refresh_token_repository

    def execute(self, refresh_token: str) -> bool:
        return self._refresh_token_repository.revoke_token(refresh_token)


class RefreshTokenUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
        token_service: TokenService,
    ):
        self._user_repository = user_repository
        self._refresh_token_repository = refresh_token_repository
        self._token_service = token_service

    def execute(self, request: RefreshTokenRequest) -> TokenResponse:
        refresh_token = self._refresh_token_repository.get_by_token(request.refresh_token)
        
        if not refresh_token or refresh_token.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        from datetime import datetime
        if refresh_token.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )

        user = self._user_repository.get_by_id(refresh_token.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )

        self._refresh_token_repository.revoke_token(request.refresh_token)
        
        new_token_pair = self._token_service.create_token_pair(user.id, user.email)
        
        new_refresh_token = RefreshToken(
            user_id=user.id,
            token=new_token_pair.refresh_token,
            expires_at=self._get_refresh_token_expiry()
        )
        
        self._refresh_token_repository.create(new_refresh_token)
        
        return TokenResponse(
            access_token=new_token_pair.access_token,
            refresh_token=new_token_pair.refresh_token,
            token_type=new_token_pair.token_type,
            expires_in=new_token_pair.expires_in
        )

    def _get_refresh_token_expiry(self):
        from datetime import datetime, timedelta
        return datetime.utcnow() + timedelta(days=7)


class GetCurrentUserUseCase:
    def __init__(self, user_repository: UserRepository):
        self._user_repository = user_repository

    def execute(self, user_id: UUID) -> UserResponse:
        user = self._user_repository.get_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at
        )
