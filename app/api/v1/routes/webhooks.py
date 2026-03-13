"""Webhook routes for API v1."""

from fastapi import APIRouter, Request, Depends
from typing import Dict, Any

from app.dependencies import get_payment_repository
from app.repositories.payment_repository import PaymentRepository
from app.middleware.rate_limiter import limiter

router = APIRouter()


@router.post("/yookassa")
@limiter.limit("1000/hour")
async def yookassa_webhook_v1(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """YooKassa webhook handler (v1)."""
    from app.payment_gateways.yookassa import handle_yookassa_webhook
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    
    result = await handle_yookassa_webhook(payload, signature)
    return {"status": "success", "message": "Webhook processed"}


@router.post("/tinkoff")
@limiter.limit("1000/hour")
async def tinkoff_webhook_v1(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """Tinkoff webhook handler (v1)."""
    from app.payment_gateways.tinkoff import handle_tinkoff_webhook
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    
    result = await handle_tinkoff_webhook(payload, signature)
    return {"status": "success", "message": "Webhook processed"}


@router.post("/cloudpayments")
@limiter.limit("1000/hour")
async def cloudpayments_webhook_v1(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """CloudPayments webhook handler (v1)."""
    from app.payment_gateways.cloudpayments import handle_cloudpayments_webhook
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    
    result = await handle_cloudpayments_webhook(payload, signature)
    return {"status": "success", "message": "Webhook processed"}


@router.post("/unitpay")
@limiter.limit("1000/hour")
async def unitpay_webhook_v1(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """UnitPay webhook handler (v1)."""
    from app.payment_gateways.unitpay import handle_unitpay_webhook
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    
    result = await handle_unitpay_webhook(payload, signature)
    return {"status": "success", "message": "Webhook processed"}


@router.post("/robokassa")
@limiter.limit("1000/hour")
async def robokassa_webhook_v1(
    request: Request,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """Robokassa webhook handler (v1)."""
    from app.payment_gateways.robokassa import handle_robokassa_webhook
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    
    result = await handle_robokassa_webhook(payload, signature)
    return {"status": "success", "message": "Webhook processed"}
