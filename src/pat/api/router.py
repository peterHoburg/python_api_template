"""Main router for the API that includes all version-specific routers."""

from fastapi import APIRouter

from pat.api.v1.router import router as v1_router

# Create the main API router
api_router = APIRouter()

# Include version-specific routers with appropriate prefixes
api_router.include_router(v1_router, prefix="/v1")

# When new API versions are added, they can be included here with their own prefixes
