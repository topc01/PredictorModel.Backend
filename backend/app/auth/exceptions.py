"""
Custom exceptions for authentication and authorization.
"""

from fastapi import HTTPException, status


class AuthError(HTTPException):
    """Base exception for authentication errors."""
    
    def __init__(self, detail: str = "Authentication error"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidTokenError(AuthError):
    """Exception raised when JWT token is invalid or expired."""
    
    def __init__(self, detail: str = "Invalid or expired token"):
        super().__init__(detail=detail)


class InsufficientPermissionsError(HTTPException):
    """Exception raised when user lacks required permissions."""
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )

