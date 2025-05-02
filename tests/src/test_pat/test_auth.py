"""Tests for the authentication utilities."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, Request, status
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from pat.utils.auth import (
    UserProfile,
    get_current_user,
    get_user_profile,
    validate_token,
)


@pytest.fixture
def mock_settings():
    """Mock the settings for Auth0."""
    with patch("pat.utils.auth.SETTINGS") as mock_settings:
        mock_settings.is_auth0_enabled.return_value = True
        mock_settings.get_auth0_domain.return_value = "test-domain.auth0.com"
        mock_settings.get_auth0_client_id.return_value = "test-client-id"
        mock_settings.get_auth0_client_secret.return_value = "test-client-secret"
        mock_settings.get_auth0_audience.return_value = "test-audience"
        mock_settings.get_auth0_callback_url.return_value = "https://example.com/callback"
        yield mock_settings


@pytest.fixture
def mock_jwks():
    """Mock JWKS for testing."""
    return {
        "keys": [
            {
                "kid": "test-kid",
                "kty": "RSA",
                "use": "sig",
                "n": "test-n",
                "e": "AQAB",
                "x5c": ["test-x5c"],
                "x5t": "test-x5t",
            }
        ]
    }


@pytest.fixture
def mock_token_payload():
    """Mock token payload for testing."""
    now = int(time.time())
    return {
        "iss": "https://test-domain.auth0.com/",
        "sub": "auth0|123456789",
        "aud": "test-audience",
        "iat": now - 100,  # Issued 100 seconds ago
        "exp": now + 3600,  # Expires in 1 hour
        "azp": "test-client-id",
        "scope": "openid profile email",
    }


@pytest.fixture
def mock_token(mock_token_payload):
    """Create a mock JWT token."""
    # This is not a real token, just a mock for testing
    header = {"alg": "RS256", "typ": "JWT", "kid": "test-kid"}
    token_bytes = (
        json.dumps(header).encode("utf-8") + b"." + json.dumps(mock_token_payload).encode("utf-8") + b"." + b"signature"
    )
    return token_bytes.decode("utf-8")


# Skip tests for get_jwks for now
# We'll focus on the tests for validate_token and other functions


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_settings")
async def test_validate_token_success(mock_jwks, mock_token):
    """Test that validate_token successfully validates a token."""
    # Mock get_jwks to return the mock JWKS
    with (
        patch("pat.utils.auth.get_jwks", return_value=mock_jwks),
        patch("auth0.authentication.token_verifier.TokenVerifier.verify"),
        patch("jose.jwt.decode") as mock_decode,
    ):
        # Mock jwt.decode to return the payload
        mock_payload = {"sub": "auth0|123456789", "exp": time.time() + 3600}
        mock_decode.return_value = mock_payload

        # Should return the payload
        result = await validate_token(mock_token)
        assert result == mock_payload


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_settings")
async def test_validate_token_expired(mock_jwks, mock_token):
    """Test that validate_token handles expired tokens."""
    # Mock get_jwks to return the mock JWKS
    with (
        patch("pat.utils.auth.get_jwks", return_value=mock_jwks),
        patch("auth0.authentication.token_verifier.TokenVerifier.verify") as mock_verify,
    ):
        # Mock verify to raise an ExpiredSignatureError
        mock_verify.side_effect = ExpiredSignatureError("Token has expired")

        # Should raise an HTTPException
        with pytest.raises(HTTPException) as excinfo:
            await validate_token(mock_token)

        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token has expired" in excinfo.value.detail


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_settings")
async def test_validate_token_invalid_claims(mock_jwks, mock_token):
    """Test that validate_token handles invalid claims."""
    # Mock get_jwks to return the mock JWKS
    with (
        patch("pat.utils.auth.get_jwks", return_value=mock_jwks),
        patch("auth0.authentication.token_verifier.TokenVerifier.verify") as mock_verify,
    ):
        # Mock verify to raise a JWTClaimsError
        mock_verify.side_effect = JWTClaimsError("Invalid audience")

        # Should raise an HTTPException
        with pytest.raises(HTTPException) as excinfo:
            await validate_token(mock_token)

        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token claims" in excinfo.value.detail


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_settings")
async def test_get_user_profile_from_token(mock_token, mock_token_payload):
    """Test that get_user_profile gets the profile from a token."""
    # Mock validate_token to return the payload
    with patch("pat.utils.auth.validate_token", return_value=mock_token_payload):
        # Should return a UserProfile
        result = await get_user_profile(mock_token)
        assert isinstance(result, UserProfile)
        assert result.sub == mock_token_payload["sub"]


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_settings")
async def test_get_user_profile_from_userinfo(mock_token):
    """Test that get_user_profile gets the profile from the userinfo endpoint."""
    # Mock validate_token to raise an error
    with (
        patch("pat.utils.auth.validate_token", side_effect=JWTError("Invalid token")),
        patch("httpx.AsyncClient.get") as mock_get,
    ):
        # Mock the userinfo response
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"sub": "auth0|123456789", "name": "Test User"}
        mock_get.return_value = mock_response

        # Should return a UserProfile
        result = await get_user_profile(mock_token)
        assert isinstance(result, UserProfile)
        assert result.sub == "auth0|123456789"
        assert result.name == "Test User"


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_settings", "mock_token_payload")
async def test_get_current_user(mock_token):
    """Test that get_current_user gets the current user."""
    # Mock get_token_from_request to return the token
    with (
        patch("pat.utils.auth.get_token_from_request", return_value=mock_token),
        patch("pat.utils.auth.validate_token"),
        patch("pat.utils.auth.get_user_profile") as mock_get_profile,
    ):
        # Mock get_user_profile to return a UserProfile
        user_profile = UserProfile(sub="auth0|123456789", name="Test User")
        mock_get_profile.return_value = user_profile

        # Create a mock request
        mock_request = MagicMock(spec=Request)

        # Should return the UserProfile
        result = await get_current_user(mock_request)
        assert result == user_profile
