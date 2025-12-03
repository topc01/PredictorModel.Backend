"""Authentication middleware for Auth0 JWT validation."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from jose.utils import base64url_decode
import httpx
from typing import Optional, Dict, Tuple
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.user import UserRole
from app.core.auth0_client import auth0_client

security = HTTPBearer()

# Cache for JWKS
_jwks_cache: Optional[dict] = None

# Cache for email/sub mapping (sub -> (email, timestamp))
_email_cache: Dict[str, Tuple[str, datetime]] = {}
CACHE_TTL = timedelta(minutes=5)  # Cache for 5 minutes


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


def _get_email_from_cache(sub: str) -> Optional[str]:
    """Get email from cache if available and not expired."""
    if sub in _email_cache:
        email, timestamp = _email_cache[sub]
        if datetime.utcnow() - timestamp < CACHE_TTL:
            return email
        else:
            # Cache expired, remove it
            del _email_cache[sub]
    return None


def _set_email_in_cache(sub: str, email: str) -> None:
    """Store email in cache."""
    _email_cache[sub] = (email, datetime.utcnow())


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Get current user from JWT token."""
    token = credentials.credentials
    payload = verify_token(token)
    
    # Extract user info from token - try multiple possible locations
    email = (
        payload.get("email") or 
        payload.get("https://email") or
        payload.get("https://your-namespace/email")
    )
    
    sub = payload.get("sub")  # Auth0 user ID
    
    # If sub is an email (contains @), use it as fallback
    if not email and sub and "@" in sub:
        email = sub
    
    # If still no email, try multiple methods in order of preference
    if not email and sub:
        # Method 1: Check cache first
        email = _get_email_from_cache(sub)
        
        # Method 2: Try /userinfo endpoint (most efficient, no rate limits)
        if not email:
            try:
                userinfo = auth0_client.get_userinfo(token)
                if userinfo and userinfo.get("email"):
                    email = userinfo.get("email")
                    _set_email_in_cache(sub, email)
            except Exception:
                pass
        
        # Method 3: Try Management API (last resort, has rate limits)
        if not email:
            try:
                url = f"https://{auth0_client.domain}/api/v2/users/{sub}"
                response = httpx.get(url, headers=auth0_client._get_headers(), timeout=5.0)
                
                if response.status_code == 200:
                    auth0_user = response.json()
                    email = auth0_user.get("email")
                    if email:
                        _set_email_in_cache(sub, email)
                elif response.status_code == 429:
                    # Rate limit - try cache again (might have been set by another request)
                    email = _get_email_from_cache(sub)
                    if not email:
                        raise HTTPException(
                            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Auth0 service temporarily unavailable (rate limited). Please try again in a moment."
                        )
            except HTTPException:
                raise
            except Exception:
                # If Management API fails, try cache one more time
                email = _get_email_from_cache(sub)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Email not found in token. Available keys: {list(payload.keys())}. Make sure to include 'email' in the token scopes or ensure the user exists in Auth0."
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


def get_user_role_from_token(payload: dict) -> Optional[UserRole]:
    """Extract user role from token payload. Returns None if role not found."""
    # Check for role in app_metadata or custom claims
    app_metadata = payload.get("https://app_metadata") or payload.get("app_metadata") or {}
    role = app_metadata.get("role")
    
    if role == "admin":
        return UserRole.ADMIN
    elif role == "viewer":
        return UserRole.VIEWER
    
    # Return None if no role found in token
    return None


def get_current_user_with_role(
    current_user: dict = Depends(get_current_user)
) -> tuple[dict, UserRole]:
    """Get current user with role from Auth0 Management API."""
    payload = current_user["payload"]
    email = current_user["email"]
    
    # Try to get role from token first
    role_from_token = get_user_role_from_token(payload)
    
    # Always consult Auth0 Management API to ensure we have the correct role
    # This is necessary because tokens don't always include app_metadata
    role = None
    try:
        role_str = auth0_client.get_user_role(email)
        if role_str:
            role = UserRole.ADMIN if role_str == "admin" else UserRole.VIEWER
    except Exception:
        # If Auth0 API fails and we have role from token, use that
        if role_from_token:
            role = role_from_token
    
    # If we still don't have a role, use token role or default to VIEWER
    if role is None:
        if role_from_token:
            role = role_from_token
        else:
            role = UserRole.VIEWER
    
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

