"""User models using Redis for storage."""
import json
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.core.redis import get_redis_client


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    USER = "user"


class User(BaseModel):
    """User model stored in Redis."""
    email: EmailStr
    name: str
    role: UserRole = UserRole.USER
    created_at: datetime
    updated_at: datetime
    
    @classmethod
    def create(cls, email: str, name: str, role: UserRole = UserRole.USER) -> "User":
        """Create a new user and save to Redis."""
        redis_client = get_redis_client()
        
        # Check if user already exists
        if redis_client.exists(f"user:{email}"):
            raise ValueError(f"User with email {email} already exists")
        
        now = datetime.utcnow()
        user = cls(
            email=email,
            name=name,
            role=role,
            created_at=now,
            updated_at=now
        )
        user.save()
        return user
    
    def save(self) -> None:
        """Save user to Redis."""
        redis_client = get_redis_client()
        self.updated_at = datetime.utcnow()
        
        # Store as hash
        redis_client.hset(
            f"user:{self.email}",
            mapping={
                "email": self.email,
                "name": self.name,
                "role": self.role.value,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat()
            }
        )
        
        # Add to users set for listing
        redis_client.sadd("users:all", self.email)
    
    @classmethod
    def get(cls, email: str) -> Optional["User"]:
        """Get user from Redis by email."""
        redis_client = get_redis_client()
        data = redis_client.hgetall(f"user:{email}")
        
        if not data:
            return None
        
        return cls(
            email=data["email"],
            name=data["name"],
            role=UserRole(data["role"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )
    
    @classmethod
    def list_all(cls, skip: int = 0, limit: int = 100) -> list["User"]:
        """List all users."""
        redis_client = get_redis_client()
        
        # Get all user emails from the set
        emails = list(redis_client.smembers("users:all"))
        
        # Apply pagination
        paginated_emails = emails[skip:skip + limit]
        
        # Fetch users
        users = []
        for email in paginated_emails:
            user = cls.get(email)
            if user:
                users.append(user)
        
        return users
    
    def update(self, name: Optional[str] = None, role: Optional[UserRole] = None) -> None:
        """Update user fields."""
        if name is not None:
            self.name = name
        if role is not None:
            self.role = role
        self.save()
    
    def delete(self) -> None:
        """Delete user from Redis."""
        redis_client = get_redis_client()
        redis_client.delete(f"user:{self.email}")
        redis_client.srem("users:all", self.email)


__all__ = ["User", "UserRole"]
