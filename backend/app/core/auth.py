"""Authentication middleware for Auth0 JWT validation."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from jose.utils import base64url_decode
import httpx
from typing import Optional
from app.core.config import settings
from app.models.user import User, UserRole

security = HTTPBearer()

# Cache for JWKS
_jwks_cache: Optional[dict] = None


def get_jwks() -> dict:
    """Get JWKS from Auth0."""
    global _jwks_cache
    if _jwks_cache is None:
        jwks_url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
        response = httpx.get(jwks_url)
        response.raise_for_status()
        _jwks_cache = response.json()
    return _jwks_cache


def get_rsa_key(token: str) -> dict:
    """Get RSA key from JWKS for token."""
    jwks = get_jwks()
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = {}
    
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
            break
    
    if not rsa_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to find appropriate key"
        )
    
    return rsa_key


def verify_token(token: str) -> dict:
    """Verify and decode JWT token."""
    try:
        rsa_key = get_rsa_key(token)
        # Convert string to list (supports comma-separated or single algorithm)
        algorithms = [alg.strip() for alg in settings.auth0_algorithms.split(',')]
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=algorithms,
            audience=settings.auth0_api_audience,
            issuer=f"https://{settings.auth0_domain}/"
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Get current user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token)
    
    # Extract user info from token
    email = payload.get("email") or payload.get("https://email")
    sub = payload.get("sub")  # Auth0 user ID
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not found in token"
        )
    
    return {
        "email": email,
        "auth0_user_id": sub,
        "name": payload.get("name") or payload.get("https://name") or email.split("@")[0],
        "payload": payload
    }


def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """Get current active user (alias for get_current_user)."""
    return current_user


def get_user_role_from_token(payload: dict) -> UserRole:
    """Extract user role from token payload."""
    # Check for role in app_metadata or custom claims
    app_metadata = payload.get("https://app_metadata") or payload.get("app_metadata") or {}
    role = app_metadata.get("role")
    
    if role == "admin":
        return UserRole.ADMIN
    elif role == "viewer":
        return UserRole.VIEWER
    
    # Default to viewer if no role found
    return UserRole.VIEWER


def get_current_user_with_role(
    current_user: dict = Depends(get_current_user)
) -> tuple[dict, UserRole]:
    """Get current user with role from token or Redis."""
    payload = current_user["payload"]
    
    # Try to get role from token
    role = get_user_role_from_token(payload)
    
    # Try to get user from Redis to get actual role
    user = User.get(current_user["email"])
    if user:
        role = user.role
    
    return current_user, role


def require_role(required_role: UserRole):
    """Dependency to require a specific role."""
    def role_checker(
        user_and_role: tuple[dict, UserRole] = Depends(get_current_user_with_role)
    ) -> dict:
        current_user, user_role = user_and_role
        
        if user_role != required_role and user_role != UserRole.ADMIN:
            # Admins can access everything
            if required_role == UserRole.VIEWER and user_role == UserRole.ADMIN:
                return current_user
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role"
            )
        
        return current_user
    
    return role_checker

