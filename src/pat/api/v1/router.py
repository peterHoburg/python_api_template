"""Router for API version 1."""

from fastapi import APIRouter

from pat.api.responses import SuccessResponse
from pat.schemas.schemas import HealthCheckResponse

# Create the main router for v1
router = APIRouter()


@router.get("/health")
async def health_check() -> SuccessResponse[HealthCheckResponse]:
    """Health check endpoint for API v1.

    Returns:
        SuccessResponse[HealthCheckResponse]: A success response containing the health status.

    """
    health_status = HealthCheckResponse(status="healthy")
    return SuccessResponse(status="success", data=health_status)
