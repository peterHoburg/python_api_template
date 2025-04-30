"""Authentication endpoints for API version 1."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from pat.api.responses import SuccessResponse
from pat.config import SETTINGS
from pat.schemas.schemas import UserProfileResponse
from pat.utils.auth import (
    UserProfile,
    exchange_code_for_token,
    get_authorization_url,
    get_current_user,
    get_user_profile,
)

# Create the auth router
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.get("/login")
async def login(
    redirect_uri: str | None = None,
    state: str | None = None,
    audience: str | None = None,
) -> RedirectResponse:
    """Redirect to Auth0 login page.

    Args:
        redirect_uri: The URI to redirect to after authentication. Defaults to the configured callback URL.
        state: A value to maintain state between the request and callback. Defaults to None.
        audience: The API audience to request access to. Defaults to the configured audience.

    Returns:
        A redirect response to the Auth0 login page.

    Raises:
        HTTPException: If Auth0 is not configured.

    """
    if not SETTINGS.is_auth0_enabled():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Auth0 integration is not configured",
        )

    try:
        auth_url = get_authorization_url(redirect_uri=redirect_uri, state=state, audience=audience)
        return RedirectResponse(url=auth_url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.get("/callback")
async def auth0_callback(
    code: str = Query(..., description="The authorization code from Auth0"),
    state: str | None = Query(None, description="The state value from the authorization request"),
    error: str | None = Query(None, description="Error code if authentication failed"),
    error_description: str | None = Query(None, description="Error description if authentication failed"),
) -> SuccessResponse[dict]:
    """Handle the callback from Auth0 after user authentication.

    Args:
        code: The authorization code from Auth0.
        state: The state value from the authorization request.
        error: Error code if authentication failed.
        error_description: Error description if authentication failed.

    Returns:
        A success response with the tokens.

    Raises:
        HTTPException: If Auth0 is not configured or authentication failed.

    """
    if not SETTINGS.is_auth0_enabled():
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Auth0 integration is not configured",
        )

    if error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {error}. {error_description or ''}",
        )

    try:
        token_response = await exchange_code_for_token(code)
        user_profile = await get_user_profile(token_response.id_token)

        # In a real application, you would store the tokens in a secure session or cookie
        # For this basic implementation, we'll just return them in the response
        return SuccessResponse(
            status="success",
            data={
                "access_token": token_response.access_token,
                "id_token": token_response.id_token,
                "refresh_token": token_response.refresh_token,
                "token_type": token_response.token_type,
                "expires_in": token_response.expires_in,
                "user_profile": user_profile.model_dump(),
            },
        )
    except (ValueError, HTTPException) as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e


@router.get("/me", response_model=SuccessResponse[UserProfileResponse])
async def get_user_info(user: UserProfile = Depends(get_current_user)) -> SuccessResponse[UserProfileResponse]:
    """Get the current user's profile.

    Args:
        user: The current user, obtained from the access token.

    Returns:
        A success response with the user profile.

    """
    user_profile = UserProfileResponse(
        sub=user.sub,
        nickname=user.nickname,
        name=user.name,
        picture=user.picture,
        email=user.email,
        email_verified=user.email_verified,
    )
    return SuccessResponse(status="success", data=user_profile)
