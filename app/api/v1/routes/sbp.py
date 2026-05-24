"""SBP (Система Быстрых Платежей) API endpoints."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from app.middleware.rate_limiter import limiter
from app.schemas.sbp import (SBPBankResponse, SBPBanksResponse,
                             SBPPaymentInfoResponse, SBPPaymentRequest,
                             SBPPaymentResponse, SBPRefundRequest,
                             SBPRefundResponse, SBPStatusEnum,
                             SBPWebhookPayload, SBPWebhookResponse)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sbp", tags=["SBP"])


@router.post("/payment", response_model=SBPPaymentResponse)
@limiter.limit("50/hour")
async def create_sbp_payment(
    request: Request,
    payment_data: SBPPaymentRequest,
) -> SBPPaymentResponse:
    """Создание платежа через СБП.

    Создаёт платёж с генерацией QR кода и payment_url для оплаты.
    """
    from app.payment_gateways.exceptions import PaymentGatewayError
    from app.payment_gateways.sbp import gateway

    try:
        result = await gateway.create_payment(
            amount=payment_data.amount,
            order_id=payment_data.order_id,
            description=payment_data.description,
            phone=payment_data.phone,
            bank_bic=payment_data.bank_bic,
            expiration_minutes=payment_data.expiration_minutes,
        )

        return SBPPaymentResponse(
            success=True,
            payment_id=result["payment_id"],
            order_id=result["order_id"],
            amount=result["amount"],
            currency=result["currency"],
            status=result["status"],
            payment_url=result.get("payment_url"),
            qr_code=result.get("qr_code"),
            expires_at=result.get("expires_at"),
            message="Payment created successfully",
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"create_sbp_payment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/payment/{payment_id}", response_model=SBPPaymentInfoResponse)
@limiter.limit("100/hour")
async def get_sbp_payment(
    request: Request,
    payment_id: str,
) -> SBPPaymentInfoResponse:
    """Получение информации о платеже СБП."""
    from app.payment_gateways.exceptions import PaymentGatewayError
    from app.payment_gateways.sbp import gateway

    try:
        result = await gateway.get_payment_info(payment_id)

        return SBPPaymentInfoResponse(
            payment_id=result["payment_id"],
            order_id=result["order_id"],
            amount=result["amount"],
            currency=result["currency"],
            status=result["status"],
            phone=result.get("phone"),
            bank_bic=result.get("bank_bic"),
            created_at=result.get("created_at"),
            paid_at=result.get("paid_at"),
            expires_at=result.get("expires_at"),
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"get_sbp_payment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/payment/order/{order_id}", response_model=SBPPaymentInfoResponse)
@limiter.limit("100/hour")
async def get_sbp_payment_by_order(
    request: Request,
    order_id: str,
) -> SBPPaymentInfoResponse:
    """Получение информации о платеже по order_id."""
    from app.payment_gateways.exceptions import PaymentGatewayError
    from app.payment_gateways.sbp import gateway

    try:
        result = await gateway.get_payment_by_order_id(order_id)

        return SBPPaymentInfoResponse(
            payment_id=result["payment_id"],
            order_id=result["order_id"],
            amount=result["amount"],
            currency=result["currency"],
            status=result["status"],
            phone=result.get("phone"),
            bank_bic=result.get("bank_bic"),
            created_at=result.get("created_at"),
            paid_at=result.get("paid_at"),
            expires_at=result.get("expires_at"),
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"get_sbp_payment_by_order failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/refund", response_model=SBPRefundResponse)
@limiter.limit("20/hour")
async def refund_sbp_payment(
    request: Request,
    refund_data: SBPRefundRequest,
) -> SBPRefundResponse:
    """Возврат платежа СБП."""
    from app.payment_gateways.exceptions import PaymentGatewayError
    from app.payment_gateways.sbp import gateway

    try:
        result = await gateway.refund_payment(
            payment_id=refund_data.payment_id,
            amount=refund_data.amount,
            reason=refund_data.reason,
        )

        return SBPRefundResponse(
            success=True,
            refund_id=result["refund_id"],
            payment_id=result["payment_id"],
            amount=result["amount"],
            status=result["status"],
            reason=result["reason"],
            message="Refund processed successfully",
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"refund_sbp_payment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/cancel/{payment_id}")
@limiter.limit("20/hour")
async def cancel_sbp_payment(
    request: Request,
    payment_id: str,
) -> Dict[str, Any]:
    """Отмена платежа СБП."""
    from app.payment_gateways.exceptions import PaymentGatewayError
    from app.payment_gateways.sbp import gateway

    try:
        result = await gateway.cancel_payment(payment_id)

        return {
            "success": True,
            "payment_id": result["payment_id"],
            "status": result["status"],
            "cancelled_at": result.get("cancelled_at"),
            "message": "Payment cancelled successfully",
        }

    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"cancel_sbp_payment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/banks", response_model=SBPBanksResponse)
@limiter.limit("200/hour")
async def get_sbp_banks(
    request: Request,
) -> SBPBanksResponse:
    """Получить список банков СБП.

    Возвращает список банков-участников СБП с BIC кодами.
    """
    from app.payment_gateways.sbp import SBPBank

    banks_data = SBPBank.get_all_banks()
    banks = [SBPBankResponse(**bank) for bank in banks_data]

    return SBPBanksResponse(banks=banks)


@router.get("/banks/{bank_code}")
@limiter.limit("200/hour")
async def get_sbp_bank_bic(
    request: Request,
    bank_code: str,
) -> Dict[str, Any]:
    """Получить BIC код банка по коду.

    bank_code: sberbank, tinkoff, alfa, vtb, etc.
    """
    from app.payment_gateways.sbp import SBPBank

    bic = SBPBank.get_bic(bank_code)

    if not bic:
        raise HTTPException(
            status_code=404,
            detail=f"Bank '{bank_code}' not found",
        )

    return {
        "code": bank_code,
        "name": bank_code.replace("_", " ").title(),
        "bic": bic,
    }


@router.post("/webhook", response_model=SBPWebhookResponse)
@limiter.limit("1000/hour")
async def handle_sbp_webhook(
    request: Request,
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
) -> SBPWebhookResponse:
    """Webhook обработчик уведомлений от СБП."""
    from app.payment_gateways.sbp import gateway

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    try:
        result = await gateway.handle_webhook(
            payload=payload,
            signature=x_signature,
            timestamp=x_timestamp,
        )

        if result.get("status") == "failed":
            raise HTTPException(status_code=400, detail=result.get("message"))

        return SBPWebhookResponse(
            status="success",
            message=result.get("message", "Webhook processed"),
            event_type=result.get("event_type"),
            payment_id=result.get("payment_id"),
            action=result.get("action"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"handle_sbp_webhook failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/qr/{payment_id}")
@limiter.limit("200/hour")
async def get_sbp_qr_code(
    request: Request,
    payment_id: str,
) -> Dict[str, Any]:
    """Получить QR код для платежа.

    Возвращает URL для скачивания QR кода.
    """
    from app.payment_gateways.sbp import gateway

    qr_url = gateway.get_qr_code_url(payment_id)

    return {
        "payment_id": payment_id,
        "qr_url": qr_url,
    }
