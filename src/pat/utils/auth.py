"""Authentication utilities for Auth0 integration.

This module provides utilities for Auth0 authentication, including:
- Generating authorization URLs
- Token exchange
- Token validation
- User profile retrieval
- Permission checking
"""

import contextlib
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, TypeVar
from urllib.parse import urlencode

import httpx
from auth0.authentication import GetToken
from auth0.authentication.token_verifier import (
    AsymmetricSignatureVerifier,
    TokenVerifier,
)
from auth0.exceptions import Auth0Error
from fastapi import HTTPException, Request, status
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pat.config import SETTINGS
from pat.models.role import Permission
from pat.models.user import User
from pat.utils.db import get_session

# JWKS cache
_JWKS_CACHE: dict[str, Any] = {}
_JWKS_CACHE_TIMESTAMP: datetime | None = None
_JWKS_CACHE_TTL = timedelta(hours=24)  # Cache JWKS for 24 hours

# Error messages
AUTH0_NOT_CONFIGURED_ERROR = "Auth0 is not configured"


class TokenResponse(BaseModel):
    """Response model for token exchange."""

    access_token: str
    id_token: str
    refresh_token: str | None = None
    token_type: str
    expires_in: int


class UserProfile(BaseModel):
    """User profile model."""

    sub: str
    nickname: str | None = None
    name: str | None = None
    picture: str | None = None
    email: str | None = None
    email_verified: bool | None = None


def get_authorization_url(
    redirect_uri: str | None = None,
    state: str | None = None,
    scope: str = "openid profile email",
    audience: str | None = None,
) -> str:
    """Generate an Auth0 authorization URL.

    Args:
        redirect_uri: The URI to redirect to after authentication. Defaults to the configured callback URL.
        state: A value to maintain state between the request and callback. Defaults to None.
        scope: The scopes to request. Defaults to "openid profile email".
        audience: The API audience to request access to. Defaults to the configured audience.

    Returns:
        The authorization URL.

    Raises:
        ValueError: If Auth0 is not configured.

    """
    if not SETTINGS.is_auth0_enabled():
        raise ValueError(AUTH0_NOT_CONFIGURED_ERROR)

    params = {
        "client_id": SETTINGS.get_auth0_client_id(),
        "response_type": "code",
        "redirect_uri": redirect_uri or SETTINGS.get_auth0_callback_url(),
        "scope": scope,
    }

    if state:
        params["state"] = state

    if audience or SETTINGS.auth0_audience:
        params["audience"] = audience or SETTINGS.get_auth0_audience()

    return f"https://{SETTINGS.get_auth0_domain()}/authorize?{urlencode(params)}"


async def exchange_code_for_token(code: str, redirect_uri: str | None = None) -> TokenResponse:
    """Exchange an authorization code for tokens.

    Args:
        code: The authorization code to exchange.
        redirect_uri: The redirect URI used in the authorization request.
            Defaults to the configured callback URL.

    Returns:
        A TokenResponse object containing the tokens.

    Raises:
        HTTPException: If the token exchange fails.
        ValueError: If Auth0 is not configured.

    """
    if not SETTINGS.is_auth0_enabled():
        raise ValueError(AUTH0_NOT_CONFIGURED_ERROR)

    try:
        auth0_domain = SETTINGS.get_auth0_domain()
        client_id = SETTINGS.get_auth0_client_id()
        client_secret = SETTINGS.get_auth0_client_secret()
        redirect_uri = redirect_uri or SETTINGS.get_auth0_callback_url()

        get_token = GetToken(auth0_domain, client_id, client_secret=client_secret)
        token_data = get_token.authorization_code(code, redirect_uri)
        return TokenResponse(**token_data)
    except Auth0Error as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to exchange code for token: {e!s}",
        ) from e


async def get_jwks() -> dict[str, Any]:
    """Get the JSON Web Key Set (JWKS) from Auth0.

    This function caches the JWKS to improve performance and reduce the number of requests to Auth0.
    The cache is refreshed after the TTL expires.

    Returns:
        The JWKS as a dictionary.

    Raises:
        HTTPException: If the JWKS cannot be retrieved.
        ValueError: If Auth0 is not configured.

    """
    global _JWKS_CACHE, _JWKS_CACHE_TIMESTAMP  # noqa: PLW0603

    if not SETTINGS.is_auth0_enabled():
        raise ValueError(AUTH0_NOT_CONFIGURED_ERROR)

    # Check if we have a valid cached JWKS
    if _JWKS_CACHE and _JWKS_CACHE_TIMESTAMP and datetime.now() - _JWKS_CACHE_TIMESTAMP < _JWKS_CACHE_TTL:  # noqa: DTZ005
        return _JWKS_CACHE

    # Fetch JWKS from Auth0
    try:
        jwks_url = f"https://{SETTINGS.get_auth0_domain()}/.well-known/jwks.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
            response.raise_for_status()
            jwks = response.json()
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to retrieve JWKS from Auth0: {e!s}",
        ) from e
    else:
        # Update cache
        _JWKS_CACHE = jwks
        _JWKS_CACHE_TIMESTAMP = datetime.now()  # noqa: DTZ005
        return jwks


async def validate_token(token: str, *, leeway: int = 30) -> dict[str, Any]:
    """Validate an access token.

    This function performs comprehensive validation of JWT tokens, including:
    - Signature verification using Auth0's JWKS
    - Issuer validation
    - Audience validation
    - Expiration time validation
    - Not before time validation
    - Issued at time validation

    Args:
        token: The access token to validate.
        leeway: The number of seconds of leeway to allow for time-based claims,
            to account for clock skew. Defaults to 30 seconds.

    Returns:
        The decoded token payload.

    Raises:
        HTTPException: If the token is invalid, with a specific error message.
        ValueError: If Auth0 is not configured.

    """
    if not SETTINGS.is_auth0_enabled():
        raise ValueError(AUTH0_NOT_CONFIGURED_ERROR)

    try:
        # Get JWKS URL
        jwks_url = f"https://{SETTINGS.get_auth0_domain()}/.well-known/jwks.json"

        # Set up token verification
        signature_verifier = AsymmetricSignatureVerifier(jwks_url)
        issuer = f"https://{SETTINGS.get_auth0_domain()}/"

        # Create token verifier with leeway for clock skew
        token_verifier = TokenVerifier(
            signature_verifier=signature_verifier,
            issuer=issuer,
            audience=SETTINGS.get_auth0_audience(),
            leeway=leeway,
        )

        # Verify the token
        token_verifier.verify(token)

        # If verification passes, decode the token to get the payload
        # We use python-jose for more detailed validation and better error messages
        payload = jwt.decode(
            token,
            key="",  # We already verified the signature with Auth0's TokenVerifier
            algorithms=["RS256"],  # Auth0 uses RS256
            audience=SETTINGS.get_auth0_audience(),
            issuer=issuer,
            options={
                "verify_signature": False,  # We already verified the signature
                "verify_aud": True,
                "verify_iat": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iss": True,
                "verify_sub": True,
                "verify_jti": True,
                "verify_at_hash": True,
                "leeway": leeway,
            },
        )

        # Additional validation checks
        if "exp" not in payload:
            raise JWTClaimsError("Token is missing expiration claim")  # noqa: TRY301, TRY003, EM101

        # Check if token is about to expire (within 5 minutes)
        if payload["exp"] - time.time() < 300:  # 5 minutes in seconds  # noqa: PLR2004
            # Log a warning that the token is about to expire
            # In a real application, you might want to refresh the token here
            pass

        return payload  # noqa: TRY300
    except ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        ) from e
    except JWTClaimsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token claims: {e!s}",
        ) from e
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e!s}",
        ) from e
    except Auth0Error as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth0 validation error: {e!s}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during token validation: {e!s}",
        ) from e


async def get_user_profile(token: str) -> UserProfile:
    """Get the user profile from Auth0.

    Args:
        token: The access token or ID token.

    Returns:
        The user profile.

    Raises:
        HTTPException: If the user profile cannot be retrieved.
        ValueError: If Auth0 is not configured.

    """
    if not SETTINGS.is_auth0_enabled():
        raise ValueError(AUTH0_NOT_CONFIGURED_ERROR)

    try:
        # Try to decode the token as an ID token first
        try:
            # For ID tokens, we can validate them fully
            payload = await validate_token(token)
            return UserProfile(**payload)
        except (JWTError, ValueError, HTTPException):
            # If it's not a valid ID token, try to get the user profile from the userinfo endpoint
            # This is useful for access tokens that don't contain user profile information
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://{SETTINGS.get_auth0_domain()}/userinfo",
                    headers={"Authorization": f"Bearer {token}"},
                )
                response.raise_for_status()
                user_data = response.json()
                return UserProfile(**user_data)
    except (httpx.HTTPError, JWTError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Failed to get user profile: {e!s}",
        ) from e


def get_token_from_request(request: Request) -> str:
    """Extract the access token from the request.

    Args:
        request: The FastAPI request object.

    Returns:
        The access token.

    Raises:
        HTTPException: If the token is not found or is invalid.

    """
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
            )
        return token  # noqa: TRY300
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
        ) from e


async def get_current_user(request: Request) -> UserProfile:
    """Get the current authenticated user.

    Args:
        request: The FastAPI request object.

    Returns:
        The user profile.

    Raises:
        HTTPException: If the user is not authenticated or the token is invalid.

    """
    token = get_token_from_request(request)
    await validate_token(token)
    return await get_user_profile(token)


async def get_db_user(session: AsyncSession, user_profile: UserProfile) -> User:
    """Get the database User object for the authenticated user.

    Args:
        session: The database session.
        user_profile: The user profile from Auth0.

    Returns:
        The User object from the database.

    Raises:
        HTTPException: If the user is not found in the database.

    """
    # Try to find the user by email
    if user_profile.email:
        stmt = select(User).where(User.email == user_profile.email)
        result = await session.execute(stmt)
        user = result.scalars().first()
        if user:
            return user

    # If user not found, raise an exception
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found in the database",
    )


async def check_permission(session: AsyncSession, user_profile: UserProfile, permission: Permission) -> bool:
    """Check if the user has the specified permission.

    Args:
        session: The database session.
        user_profile: The user profile from Auth0.
        permission: The permission to check.

    Returns:
        True if the user has the permission, False otherwise.

    """
    try:
        user = await get_db_user(session, user_profile)
        return await user.has_permission(session, permission)
    except HTTPException:
        # If the user is not found, they don't have the permission
        return False


T = TypeVar("T", bound=Callable[..., Any])


def permission_required(permission: Permission) -> Callable[[T], T]:
    """Decorator to check if the user has the required permission.

    Args:
        permission: The permission required to access the endpoint.

    Returns:
        A decorator function.

    """

    def decorator(func: T) -> T:
        @wraps(func)
        async def wrapper(
            request: Request,
            *args: object,
            **kwargs: object,
        ) -> object:
            # Get the database session
            session_generator = get_session()
            session = await session_generator.__anext__()

            try:
                # Get the current user
                user_profile = await get_current_user(request)

                # Check if the user has the required permission
                has_permission = await check_permission(session, user_profile, permission)
                if not has_permission:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {permission.value} is required",
                    )

                # Call the original function
                return await func(request, session, *args, **kwargs)
            finally:
                # Clean up the session
                with contextlib.suppress(StopAsyncIteration):
                    await session_generator.__anext__()

        return wrapper  # type: ignore[return-value]

    return decorator
