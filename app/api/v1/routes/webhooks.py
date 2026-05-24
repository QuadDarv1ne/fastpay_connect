"""Webhook routes for API v1."""

from fastapi import APIRouter, Request, Depends, HTTPException
from typing import Dict, Any

from app.dependencies import get_payment_repository
from app.repositories.payment_repository import PaymentRepository
from app.middleware.rate_limiter import limiter
from app.utils.gateway_registry import STATUS_MAP, EVENT_STATUS_MAP, extract_webhook_event_id

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


async def _handle_webhook(
    request: Request,
    handler_func,
    repository: PaymentRepository,
    use_gateway_instance: bool = False,
) -> Dict[str, Any]:
    """Generic webhook handler with DB status update."""
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    timestamp = request.headers.get("X-Timestamp", "")

    if use_gateway_instance:
        result = await handler_func(payload, signature, timestamp)
    else:
        result = await handler_func(payload, signature)

    # Update payment status in DB based on webhook result
    if result.get("status") == "processed" or result.get("processed"):
        order_id = payload.get("order_id") or payload.get("payment_id") or result.get("order_id")
        if order_id:
            # Prefer direct event mapping, fallback to message-based lookup
            event = payload.get("event", "")
            db_status = EVENT_STATUS_MAP.get(event) or STATUS_MAP.get(
                result.get("message", "").lower(), "pending"
            )
            webhook_event_id = extract_webhook_event_id(payload)
            repository.update_status(
                order_id=order_id,
                status=db_status,
                metadata=payload,
                webhook_event_id=webhook_event_id,
            )
            logger.info(f"Payment {order_id} status updated to {db_status}")

    if result.get("status") == "failed":
        raise HTTPException(status_code=400, detail=result.get("message"))

    return {"status": "success", "message": result.get("message", "Webhook processed"), "result": result}


@router.post("/yookassa")
@limiter.limit("1000/hour")
async def yookassa_webhook_v1(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """YooKassa webhook handler (v1)."""
    from app.payment_gateways.yookassa import handle_yookassa_webhook
    return await _handle_webhook(request, handle_yookassa_webhook, repository)


@router.post("/tinkoff")
@limiter.limit("1000/hour")
async def tinkoff_webhook_v1(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """Tinkoff webhook handler (v1)."""
    from app.payment_gateways.tinkoff import handle_tinkoff_webhook
    return await _handle_webhook(request, handle_tinkoff_webhook, repository)


@router.post("/cloudpayments")
@limiter.limit("1000/hour")
async def cloudpayments_webhook_v1(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """CloudPayments webhook handler (v1)."""
    from app.payment_gateways.cloudpayments import handle_cloudpayments_webhook
    return await _handle_webhook(request, handle_cloudpayments_webhook, repository)


@router.post("/unitpay")
@limiter.limit("1000/hour")
async def unitpay_webhook_v1(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """UnitPay webhook handler (v1)."""
    from app.payment_gateways.unitpay import handle_unitpay_webhook
    return await _handle_webhook(request, handle_unitpay_webhook, repository)


@router.post("/robokassa")
@limiter.limit("1000/hour")
async def robokassa_webhook_v1(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """Robokassa webhook handler (v1)."""
    from app.payment_gateways.robokassa import handle_robokassa_webhook
    return await _handle_webhook(request, handle_robokassa_webhook, repository)


@router.post("/rustore")
@limiter.limit("1000/hour")
async def rustore_webhook_v1(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """RuStore webhook handler (v1)."""
    from app.payment_gateways.rustore import gateway
    return await _handle_webhook(request, gateway.handle_webhook, repository)


@router.post("/sbp")
@limiter.limit("1000/hour")
async def sbp_webhook_v1(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """SBP webhook handler (v1)."""
    from app.payment_gateways.sbp import gateway
    return await _handle_webhook(request, gateway.handle_webhook, repository, use_gateway_instance=True)
