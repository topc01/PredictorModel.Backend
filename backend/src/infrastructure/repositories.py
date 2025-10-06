from typing import Optional, List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from ..domain.entities import User, RefreshToken
from ..domain.repositories import UserRepository, RefreshTokenRepository
from .database import UserModel, RefreshTokenModel


class SQLUserRepository(UserRepository):
    def __init__(self, db: Session):
        self._db = db

    def create(self, user: User) -> User:
        db_user = UserModel(
            id=user.id,
            email=user.email,
            username=user.username,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at
        )
        self._db.add(db_user)
        self._db.commit()
        self._db.refresh(db_user)
        return self._to_entity(db_user)

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        db_user = self._db.query(UserModel).filter(UserModel.id == user_id).first()
        return self._to_entity(db_user) if db_user else None

    def get_by_email(self, email: str) -> Optional[User]:
        db_user = self._db.query(UserModel).filter(UserModel.email == email).first()
        return self._to_entity(db_user) if db_user else None

    def get_by_username(self, username: str) -> Optional[User]:
        db_user = self._db.query(UserModel).filter(UserModel.username == username).first()
        return self._to_entity(db_user) if db_user else None

    def update(self, user: User) -> User:
        db_user = self._db.query(UserModel).filter(UserModel.id == user.id).first()
        if db_user:
            db_user.email = user.email
            db_user.username = user.username
            db_user.hashed_password = user.hashed_password
            db_user.is_active = user.is_active
            db_user.is_verified = user.is_verified
            db_user.updated_at = datetime.utcnow()
            self._db.commit()
            self._db.refresh(db_user)
        return self._to_entity(db_user)

    def delete(self, user_id: UUID) -> bool:
        db_user = self._db.query(UserModel).filter(UserModel.id == user_id).first()
        if db_user:
            self._db.delete(db_user)
            self._db.commit()
            return True
        return False

    def _to_entity(self, db_user: UserModel) -> User:
        return User(
            id=db_user.id,
            email=db_user.email,
            username=db_user.username,
            hashed_password=db_user.hashed_password,
            is_active=db_user.is_active,
            is_verified=db_user.is_verified,
            created_at=db_user.created_at,
            updated_at=db_user.updated_at
        )


class SQLRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, db: Session):
        self._db = db

    def create(self, refresh_token: RefreshToken) -> RefreshToken:
        db_token = RefreshTokenModel(
            id=refresh_token.id,
            user_id=refresh_token.user_id,
            token=refresh_token.token,
            expires_at=refresh_token.expires_at,
            is_revoked=refresh_token.is_revoked,
            created_at=refresh_token.created_at
        )
        self._db.add(db_token)
        self._db.commit()
        self._db.refresh(db_token)
        return self._to_entity(db_token)

    def get_by_token(self, token: str) -> Optional[RefreshToken]:
        db_token = self._db.query(RefreshTokenModel).filter(RefreshTokenModel.token == token).first()
        return self._to_entity(db_token) if db_token else None

    def get_by_user_id(self, user_id: UUID) -> List[RefreshToken]:
        db_tokens = self._db.query(RefreshTokenModel).filter(RefreshTokenModel.user_id == user_id).all()
        return [self._to_entity(token) for token in db_tokens]

    def revoke_token(self, token: str) -> bool:
        db_token = self._db.query(RefreshTokenModel).filter(RefreshTokenModel.token == token).first()
        if db_token:
            db_token.is_revoked = True
            self._db.commit()
            return True
        return False

    def revoke_all_user_tokens(self, user_id: UUID) -> bool:
        self._db.query(RefreshTokenModel).filter(
            and_(RefreshTokenModel.user_id == user_id, RefreshTokenModel.is_revoked == False)
        ).update({"is_revoked": True})
        self._db.commit()
        return True

    def delete_expired_tokens(self) -> int:
        now = datetime.utcnow()
        expired_tokens = self._db.query(RefreshTokenModel).filter(
            RefreshTokenModel.expires_at < now
        ).all()
        count = len(expired_tokens)
        for token in expired_tokens:
            self._db.delete(token)
        self._db.commit()
        return count

    def _to_entity(self, db_token: RefreshTokenModel) -> RefreshToken:
        return RefreshToken(
            id=db_token.id,
            user_id=db_token.user_id,
            token=db_token.token,
            expires_at=db_token.expires_at,
            is_revoked=db_token.is_revoked,
            created_at=db_token.created_at
        )
