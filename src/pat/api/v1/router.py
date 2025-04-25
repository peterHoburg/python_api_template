"""Router for API version 1."""

from fastapi import APIRouter

# Create the main router for v1
router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint for API v1.

    Returns:
        dict: A dictionary with a status message.

    """
    return {"status": "healthy"}
