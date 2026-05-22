"""
API Version 2 (v2) - Development API.

This is the development version of the FastPay Connect API.
Endpoints in this version may change without notice.
"""

from fastapi import APIRouter

from app.api.v2.routes import (
    health,
    payments,
    webhooks,
    admin,
    i18n,
)

router = APIRouter()

# Include v2 routes
router.include_router(health.router, tags=["Health v2"])
router.include_router(payments.router, prefix="/payments", tags=["Payments v2"])
router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks v2"])
router.include_router(admin.router, prefix="/admin", tags=["Admin v2"])
router.include_router(i18n.router, prefix="/i18n", tags=["i18n v2"])


@router.get("/", tags=["Info v2"])
async def api_v2_info():
    """Information about API v2."""
    return {
        "version": "2.0.0",
        "status": "development",
        "message": "API v2 is under development.",
        "available_endpoints": [
            "/api/v2/health - Enhanced health check",
            "/api/v2/ready - Readiness check",
            "/api/v2/live - Liveness check",
            "POST /api/v2/payments/create - Create payment (idempotency support)",
            "GET  /api/v2/payments/{order_id} - Payment status",
            "POST /api/v2/payments/{order_id}/idempotency - Idempotency probe",
            "POST /api/v2/webhooks/{gateway} - Webhook (9 gateways)",
            "GET  /api/v2/admin/statistics - Payment statistics",
            "POST /api/v2/admin/refund - Refund payment",
            "POST /api/v2/admin/cancel - Cancel payment",
            "GET  /api/v2/admin/audit-logs - Audit log",
            "GET  /api/v2/i18n/translations - Get all translations",
            "GET  /api/v2/i18n/languages - Get supported languages",
            "GET  /api/v2/i18n/translate/{key} - Translate specific key",
        ],
    }


__all__ = ["router"]
