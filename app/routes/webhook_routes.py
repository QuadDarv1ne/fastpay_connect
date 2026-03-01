from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request, Depends, status
from app.payment_gateways.yookassa import handle_yookassa_webhook
from app.payment_gateways.tinkoff import handle_tinkoff_webhook
from app.payment_gateways.cloudpayments import handle_cloudpayments_webhook
from app.payment_gateways.unitpay import handle_unitpay_webhook
from app.payment_gateways.robokassa import handle_robokassa_webhook
from app.database import get_db
from app.services.payment_service import update_payment_status
from app.utils.ip_validator import verify_webhook_ip
from app.config import YOOKASSA_IPS, TINKOFF_IPS, CLOUDPAYMENTS_IPS, UNITPAY_IPS, ROBOKASSA_IPS
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

IP_WHITELISTS: Dict[str, List[str]] = {
    "yookassa": YOOKASSA_IPS,
    "tinkoff": TINKOFF_IPS,
    "cloudpayments": CLOUDPAYMENTS_IPS,
    "unitpay": UNITPAY_IPS,
    "robokassa": ROBOKASSA_IPS,
}

STATUS_MAP: Dict[str, str] = {
    "payment successful": "completed",
    "payment canceled": "cancelled",
    "payment failed": "failed",
    "payment refunded": "refunded",
}


async def process_webhook(
    payment_system: str,
    payload: Dict[str, Any],
    signature: str,
    db: Session
) -> Dict[str, str]:
    """Обработка webhook уведомления."""
    handlers = {
        "yookassa": handle_yookassa_webhook,
        "tinkoff": handle_tinkoff_webhook,
        "cloudpayments": handle_cloudpayments_webhook,
        "unitpay": handle_unitpay_webhook,
        "robokassa": handle_robokassa_webhook,
    }

    handler = handlers.get(payment_system)
    if not handler:
        logger.error(f"Unknown payment system: {payment_system}")
        raise HTTPException(status_code=400, detail="Unknown payment system")

    try:
        result = await handler(payload, signature)
    except Exception as e:
        logger.error(f"Webhook handler error: {e}")
        raise HTTPException(status_code=400, detail=f"Webhook processing failed: {e}")

    if result.get("status") == "processed":
        order_id: Optional[str] = payload.get("order_id") or payload.get("payment_id")
        if order_id:
            message = result.get("message", "").lower()
            db_status = STATUS_MAP.get(message, "pending")
            update_payment_status(db=db, order_id=order_id, status=db_status, metadata=payload)
            logger.info(f"Payment {order_id} status updated to {db_status}")

    return result


@router.post("/yookassa")
async def yookassa_webhook(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Webhook от YooKassa."""
    await verify_webhook_ip(request, IP_WHITELISTS["yookassa"])
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    result = await process_webhook("yookassa", payload, signature, db)
    return {"status": "success", "message": result.get("message", "")}


@router.post("/tinkoff")
async def tinkoff_webhook(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Webhook от Tinkoff."""
    await verify_webhook_ip(request, IP_WHITELISTS["tinkoff"])
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    result = await process_webhook("tinkoff", payload, signature, db)
    return {"status": "success", "message": result.get("message", "")}


@router.post("/cloudpayments")
async def cloudpayments_webhook(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Webhook от CloudPayments."""
    await verify_webhook_ip(request, IP_WHITELISTS["cloudpayments"])
    payload = await request.json()
    token = payload.get("token", request.headers.get("X-Signature", ""))
    result = await process_webhook("cloudpayments", payload, token, db)
    return {"status": "success", "message": result.get("message", "")}


@router.post("/unitpay")
async def unitpay_webhook(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Webhook от UnitPay."""
    await verify_webhook_ip(request, IP_WHITELISTS["unitpay"])
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    result = await process_webhook("unitpay", payload, signature, db)
    return {"status": "success", "message": result.get("message", "")}


@router.post("/robokassa")
async def robokassa_webhook(request: Request, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Webhook от Robokassa."""
    await verify_webhook_ip(request, IP_WHITELISTS["robokassa"])
    payload = await request.json()
    signature = request.headers.get("X-Signature", "")
    result = await process_webhook("robokassa", payload, signature, db)
    return {"status": "success", "message": result.get("message", "")}
