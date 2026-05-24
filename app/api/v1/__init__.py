"""
API Version 1 (v1) - Stable API.

This is the first stable version of the FastPay Connect API.
All endpoints in this version are considered stable and backward-compatible.
"""

from fastapi import APIRouter

from app.api.v1.routes import (admin, apple_pay, auth, currencies, google_pay,
                               health, payments, rustore, sbp, tenants,
                               webhooks)

router = APIRouter()

# Include all v1 routes
router.include_router(payments.router, prefix="/payments", tags=["Payments v1"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks v1"])
router.include_router(admin.router, prefix="/admin", tags=["Admin v1"])
router.include_router(auth.router, prefix="/auth", tags=["Authentication v1"])
router.include_router(health.router, tags=["Health v1"])
router.include_router(currencies.router, prefix="/currencies", tags=["Currencies v1"])
router.include_router(rustore.router, prefix="/rustore", tags=["RuStore v1"])
router.include_router(sbp.router, prefix="/sbp", tags=["SBP v1"])
router.include_router(tenants.router, prefix="/tenants", tags=["Tenants v1"])
router.include_router(apple_pay.router, tags=["Apple Pay v1"])
router.include_router(google_pay.router, tags=["Google Pay v1"])


__all__ = ["router"]
