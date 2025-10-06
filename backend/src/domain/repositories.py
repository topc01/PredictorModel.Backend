from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from .entities import User, RefreshToken


class UserRepository(ABC):
    @abstractmethod
    def create(self, user: User) -> User:
        pass

    @abstractmethod
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        pass

    @abstractmethod
    def update(self, user: User) -> User:
        pass

    @abstractmethod
    def delete(self, user_id: UUID) -> bool:
        pass


class RefreshTokenRepository(ABC):
    @abstractmethod
    def create(self, refresh_token: RefreshToken) -> RefreshToken:
        pass

    @abstractmethod
    def get_by_token(self, token: str) -> Optional[RefreshToken]:
        pass

    @abstractmethod
    def get_by_user_id(self, user_id: UUID) -> List[RefreshToken]:
        pass

    @abstractmethod
    def revoke_token(self, token: str) -> bool:
        pass

    @abstractmethod
    def revoke_all_user_tokens(self, user_id: UUID) -> bool:
        pass

    @abstractmethod
    def delete_expired_tokens(self) -> int:
        pass
