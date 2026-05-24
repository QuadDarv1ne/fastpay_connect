"""Webhook routes for API v2.

Improvements over v1:
- All 9 payment gateways registered
- Request tracing via X-Request-Id header
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request

from app.dependencies import get_payment_repository
from app.middleware.rate_limiter import limiter
from app.repositories.payment_repository import PaymentRepository
from app.utils.gateway_registry import (EVENT_STATUS_MAP, STATUS_MAP,
                                        WEBHOOK_HANDLERS,
                                        extract_webhook_event_id)

logger = logging.getLogger(__name__)

router = APIRouter()

ALL_GATEWAYS = (
    "yookassa", "tinkoff", "cloudpayments", "unitpay", "robokassa",
    "sbp", "rustore", "apple_pay", "google_pay",
)


def _create_webhook_handler(gateway_name: str):
    """Factory to create a webhook handler with correct gateway closure."""

    @limiter.limit("1000/hour")
    async def webhook_handler(
        request: Request,
        repository: PaymentRepository = Depends(get_payment_repository),
    ) -> Dict[str, Any]:
        payload = await request.json()
        signature = request.headers.get("X-Signature", "")
        timestamp = request.headers.get("X-Timestamp", "")
        request_id = request.headers.get("X-Request-Id", "")

        handler = WEBHOOK_HANDLERS.get(gateway_name)
        if not handler:
            logger.warning(f"No webhook handler registered for {gateway_name}")
            return {"status": "error", "message": f"Unknown gateway: {gateway_name}"}

        try:
            result = await handler(payload, signature, timestamp)
        except Exception as e:
            logger.error(f"Webhook error for {gateway_name}: {e}")
            return {"status": "error", "message": str(e)}

        if result.get("status") == "processed" or result.get("processed"):
            order_id = payload.get("order_id") or payload.get("payment_id") or result.get("order_id")
            if order_id:
                # Prefer direct event mapping, fallback to message-based lookup
                event = payload.get("event", "")
                db_status = EVENT_STATUS_MAP.get(event) or STATUS_MAP.get(
                    result.get("message", "").lower(), "pending"
                )
                webhook_event_id = extract_webhook_event_id(payload)
                payment = repository.update_status(
                    order_id=order_id,
                    status=db_status,
                    metadata=payload,
                    webhook_event_id=webhook_event_id,
                )
                if payment:
                    repository.db.commit()
                    repository.db.refresh(payment)
                logger.info(f"[{request_id}] Payment {order_id} -> {db_status}")

        return {
            "status": "ok",
            "gateway": gateway_name,
            "processed": result.get("status") == "processed",
            "order_id": payload.get("order_id"),
        }

    return webhook_handler


# Register all 9 gateway webhook endpoints
for _gw_name in ALL_GATEWAYS:
    router.post(f"/{_gw_name}")(_create_webhook_handler(_gw_name))
