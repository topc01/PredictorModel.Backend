"""
FastAPI dependencies for authentication and authorization.
"""

from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from functools import lru_cache

from app.auth.config import auth0_settings
from app.auth.exceptions import AuthError, InvalidTokenError, InsufficientPermissionsError

# Security scheme for Bearer token
security = HTTPBearer()


@lru_cache()
def get_jwks():
    """
    Fetch and cache Auth0 JWKS (JSON Web Key Set) for token verification.
    
    Returns:
        dict: JWKS containing public keys
    """
    try:
        response = httpx.get(auth0_settings.jwks_url, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise AuthError(f"Failed to fetch JWKS: {str(e)}")


def get_rsa_key(token: str) -> dict:
    """
    Get the RSA key from JWKS that matches the token's key ID.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: RSA public key
    """
    try:
        # Decode token header without verification
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise InvalidTokenError("Token missing key ID")
        
        # Get JWKS
        jwks = get_jwks()
        
        # Find the key with matching kid
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key.get("use", "sig"),
                    "n": key["n"],
                    "e": key["e"],
                }
        
        raise InvalidTokenError("Unable to find appropriate key")
    except JWTError as e:
        raise InvalidTokenError(f"Invalid token format: {str(e)}")


def verify_token(token: str) -> dict:
    """
    Verify and decode JWT token from Auth0.
    
    Args:
        token: JWT token string
        
    Returns:
        dict: Decoded token payload
        
    Raises:
        InvalidTokenError: If token is invalid or expired
    """
    try:
        # Get RSA key
        rsa_key = get_rsa_key(token)
        
        # Verify and decode token
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=auth0_settings.algorithms,
            audience=auth0_settings.api_audience,
            issuer=auth0_settings.issuer,
        )
        
        return payload
    except jwt.ExpiredSignatureError:
        raise InvalidTokenError("Token has expired")
    except jwt.JWTClaimsError as e:
        raise InvalidTokenError(f"Token claims invalid: {str(e)}")
    except JWTError as e:
        raise InvalidTokenError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise InvalidTokenError(f"Token verification failed: {str(e)}")


def get_user_roles(payload: dict) -> List[str]:
    """
    Extract user roles from JWT token payload.
    
    Auth0 stores roles in a namespaced claim: https://your-domain/roles
    
    Args:
        payload: Decoded JWT payload
        
    Returns:
        List[str]: List of user roles
    """
    # Try different possible claim names for roles
    role_claims = [
        f"https://{auth0_settings.domain}/roles",  # Auth0 RBAC namespace
        "https://your-domain/roles",  # Generic namespace
        "roles",  # Direct claim
        "permissions",  # Alternative claim name
    ]
    
    for claim in role_claims:
        if claim in payload:
            roles = payload[claim]
            if isinstance(roles, list):
                return roles
            elif isinstance(roles, str):
                return [roles]
    
    # If no roles found, return empty list
    return []


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    FastAPI dependency to get current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer token credentials
        
    Returns:
        dict: User information from token payload
        
    Raises:
        InvalidTokenError: If token is invalid
    """
    token = credentials.credentials
    payload = verify_token(token)
    
    # Extract user information
    user_info = {
        "sub": payload.get("sub"),  # Auth0 user ID
        "email": payload.get("email"),
        "roles": get_user_roles(payload),
        "permissions": payload.get("permissions", []),
    }
    
    return user_info


def require_role(allowed_roles: List[str]):
    """
    Create a dependency that requires the user to have one of the specified roles.
    
    Args:
        allowed_roles: List of role names that are allowed
        
    Returns:
        FastAPI dependency function
    """
    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        user_roles = user.get("roles", [])
        
        # Check if user has any of the allowed roles
        if not any(role in allowed_roles for role in user_roles):
            raise InsufficientPermissionsError(
                f"Required role: one of {allowed_roles}. User has: {user_roles}"
            )
        
        return user
    
    return role_checker


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """
    FastAPI dependency that requires administrator role.
    
    Args:
        user: Current authenticated user
        
    Returns:
        dict: User information
        
    Raises:
        InsufficientPermissionsError: If user is not an administrator
    """
    user_roles = user.get("roles", [])
    
    if "administrador" not in user_roles:
        raise InsufficientPermissionsError(
            "Administrator role required"
        )
    
    return user

