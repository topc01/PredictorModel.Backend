"""
Auth0 authentication and authorization module.

This module provides JWT verification, role-based access control,
and user management integration with Auth0.
"""

from app.auth.dependencies import get_current_user, require_role, require_admin
from app.auth.exceptions import AuthError, InsufficientPermissionsError, InvalidTokenError
from app.auth.config import auth0_settings

__all__ = [
    "get_current_user",
    "require_role",
    "require_admin",
    "AuthError",
    "InsufficientPermissionsError",
    "InvalidTokenError",
    "auth0_settings",
]

