"""
API Version 1 (v1) - Stable API.

This is the first stable version of the FastPay Connect API.
All endpoints in this version are considered stable and backward-compatible.
"""

from fastapi import APIRouter

from app.api.v1.routes import (
    payments,
    webhooks,
    admin,
    auth,
    health,
)

router = APIRouter()

# Include all v1 routes
router.include_router(payments.router, prefix="/payments", tags=["Payments v1"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks v1"])
router.include_router(admin.router, prefix="/admin", tags=["Admin v1"])
router.include_router(auth.router, prefix="/auth", tags=["Authentication v1"])
router.include_router(health.router, tags=["Health v1"])

__all__ = ["router"]
