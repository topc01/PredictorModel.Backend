"""User roles."""
from enum import Enum

class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    VIEWER = "viewer"

__all__ = ["UserRole"]
