"""
API Version 2 (v2) - Development API.

This is the development version of the FastPay Connect API.
Endpoints in this version may change without notice.
"""

from fastapi import APIRouter

# v2 routes will be added here in the future
# For now, we just expose the same as v1 for backward compatibility

router = APIRouter()

@router.get("/", tags=["Info v2"])
async def api_v2_info():
    """Information about API v2."""
    return {
        "version": "2.0.0",
        "status": "development",
        "message": "API v2 is under development. Please use v1 for stable endpoints.",
    }

__all__ = ["router"]
