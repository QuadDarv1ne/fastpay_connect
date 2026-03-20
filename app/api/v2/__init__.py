"""
API Version 2 (v2) - Development API.

This is the development version of the FastPay Connect API.
Endpoints in this version may change without notice.
"""

from fastapi import APIRouter

from app.api.v2.routes import (
    health,
)

router = APIRouter()

# Include v2 routes (under development)
router.include_router(health.router, tags=["Health v2"])


@router.get("/", tags=["Info v2"])
async def api_v2_info():
    """Information about API v2."""
    return {
        "version": "2.0.0",
        "status": "development",
        "message": "API v2 is under development. Please use v1 for stable endpoints.",
        "available_endpoints": [
            "/api/v2/health - Health check (v2)",
        ],
    }


__all__ = ["router"]
