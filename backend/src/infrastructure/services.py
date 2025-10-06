from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..domain.services import PasswordService, TokenService
from ..domain.entities import Token
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class BcryptPasswordService(PasswordService):
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, password: str, hashed_password: str) -> bool:
        return pwd_context.verify(password, hashed_password)


class JWTTokenService(TokenService):
    def create_access_token(self, user_id: UUID, email: str) -> str:
        to_encode = {
            "sub": str(user_id),
            "email": email,
            "exp": datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    def create_refresh_token(self, user_id: UUID) -> str:
        to_encode = {
            "sub": str(user_id),
            "exp": datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    def verify_token(self, token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            return payload
        except JWTError:
            return None

    def create_token_pair(self, user_id: UUID, email: str) -> Token:
        access_token = self.create_access_token(user_id, email)
        refresh_token = self.create_refresh_token(user_id)
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60
        )
