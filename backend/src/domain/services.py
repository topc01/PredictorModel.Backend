from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID
from .entities import User, Token


class PasswordService(ABC):
    @abstractmethod
    def hash_password(self, password: str) -> str:
        pass

    @abstractmethod
    def verify_password(self, password: str, hashed_password: str) -> bool:
        pass


class TokenService(ABC):
    @abstractmethod
    def create_access_token(self, user_id: UUID, email: str) -> str:
        pass

    @abstractmethod
    def create_refresh_token(self, user_id: UUID) -> str:
        pass

    @abstractmethod
    def verify_token(self, token: str) -> Optional[dict]:
        pass

    @abstractmethod
    def create_token_pair(self, user_id: UUID, email: str) -> Token:
        pass
