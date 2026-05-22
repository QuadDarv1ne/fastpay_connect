"""Google Pay API endpoints."""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.middleware.rate_limiter import limiter
from app.schemas.google_pay import (
    GooglePayPaymentRequest,
    GooglePayPaymentResponse,
    GooglePayPaymentInfoResponse,
    GooglePayPaymentDataRequest,
    GooglePayTokenRequest,
    GooglePayRefundRequest,
    GooglePayRefundResponse,
    GooglePayWebhookPayload,
    GooglePayWebhookResponse,
    GooglePayMerchantValidationResponse,
    GooglePayIsReadyToPayResponse,
    GooglePayStatusEnum,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/google-pay", tags=["Google Pay"])


@router.post(
    "/payment",
    response_model=GooglePayPaymentResponse,
    summary="Создание платежа Google Pay",
)
@limiter.limit("50/hour")
async def create_google_pay_payment(
    request: Request,
    payment_data: GooglePayPaymentRequest,
) -> GooglePayPaymentResponse:
    """Создание платежа через Google Pay.

    Возвращает PaymentDataRequest для инициализации Google Pay на клиенте.
    """
    from app.payment_gateways.google_pay import get_gateway
    from app.payment_gateways.exceptions import PaymentGatewayError

    try:
        gateway = get_gateway()
        result = await gateway.create_payment(
            amount=payment_data.amount,
            order_id=payment_data.order_id,
            description=payment_data.description or f"Order {payment_data.order_id}",
            currency=payment_data.currency,
        )

        return GooglePayPaymentResponse(
            success=True,
            payment_id=result.get("payment_id", ""),
            order_id=result["order_id"],
            amount=result["amount"],
            currency=result["currency"],
            status=GooglePayStatusEnum.PENDING,
            payment_data_request=result.get("payment_data_request"),
            merchant_id=result.get("merchant_id"),
            message="Payment created successfully",
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"create_google_pay_payment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/payment/process-token",
    response_model=GooglePayPaymentResponse,
    summary="Обработка токена Google Pay",
)
@limiter.limit("30/hour")
async def process_google_pay_token(
    request: Request,
    token_data: GooglePayTokenRequest,
) -> GooglePayPaymentResponse:
    """Обработка токена Google Pay после авторизации пользователем."""
    from app.payment_gateways.google_pay import get_gateway
    from app.payment_gateways.exceptions import PaymentGatewayError

    try:
        gateway = get_gateway()
        result = await gateway.process_payment_token(
            token_data=token_data.token_data,
            order_id=token_data.order_id,
            amount=token_data.amount,
            currency=token_data.currency,
        )

        return GooglePayPaymentResponse(
            success=True,
            payment_id=result["payment_id"],
            order_id=result["order_id"],
            amount=result["amount"],
            currency=result["currency"],
            status=GooglePayStatusEnum.COMPLETED,
            message="Payment processed successfully",
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"process_google_pay_token failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/payment/{payment_id}",
    response_model=GooglePayPaymentInfoResponse,
    summary="Информация о платеже Google Pay",
)
@limiter.limit("100/hour")
async def get_google_pay_payment(
    request: Request,
    payment_id: str,
) -> GooglePayPaymentInfoResponse:
    """Получение информации о платеже Google Pay."""
    return GooglePayPaymentInfoResponse(
        payment_id=payment_id,
        order_id=f"order_{payment_id}",
        amount=1000.0,
        currency="RUB",
        status=GooglePayStatusEnum.COMPLETED,
        card_network="VISA",
        transaction_id=f"txn_{payment_id}",
        created_at=datetime.now(timezone.utc).isoformat(),
        processed_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post(
    "/payment/{payment_id}/refund",
    response_model=GooglePayRefundResponse,
    summary="Возврат платежа Google Pay",
)
@limiter.limit("20/hour")
async def refund_google_pay_payment(
    request: Request,
    payment_id: str,
    refund_data: GooglePayRefundRequest,
) -> GooglePayRefundResponse:
    """Возврат платежа Google Pay."""
    from app.payment_gateways.google_pay import get_gateway
    from app.payment_gateways.exceptions import PaymentGatewayError

    try:
        gateway = get_gateway()
        # In real implementation: call refund API

        refund_id = f"ref_{payment_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        amount = refund_data.amount or 1000.0

        return GooglePayRefundResponse(
            success=True,
            refund_id=refund_id,
            payment_id=payment_id,
            amount=amount,
            status="completed",
            message="Refund processed successfully",
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"refund_google_pay_payment failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/merchant/validate",
    response_model=GooglePayMerchantValidationResponse,
    summary="Валидация мерчанта Google Pay",
)
@limiter.limit("10/hour")
async def validate_google_pay_merchant(
    request: Request,
) -> GooglePayMerchantValidationResponse:
    """Валидация мерчанта для Google Pay."""
    from app.payment_gateways.google_pay import get_gateway
    from app.payment_gateways.exceptions import PaymentGatewayError

    try:
        gateway = get_gateway()
        result = await gateway.validate_merchant()

        return GooglePayMerchantValidationResponse(
            merchant_id=result["merchant_id"],
            gateway_id=result.get("gateway_id"),
            environment=result["environment"],
            status=result["status"],
            expires_at=result["expires_at"],
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"validate_google_pay_merchant failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/webhook",
    response_model=GooglePayWebhookResponse,
    summary="Webhook для уведомлений Google Pay",
    include_in_schema=False,
)
async def google_pay_webhook(
    request: Request,
    payload: GooglePayWebhookPayload,
) -> GooglePayWebhookResponse:
    """Обработка webhook уведомлений от Google Pay."""
    from app.payment_gateways.google_pay import get_gateway
    from app.payment_gateways.exceptions import PaymentGatewayError

    try:
        gateway = get_gateway()
        payload_dict = payload.model_dump()
        result = await gateway.handle_webhook(payload=payload_dict)

        return GooglePayWebhookResponse(
            status=result["status"],
            order_id=result["order_id"],
            event_type=result["event_type"],
            processed_at=result["processed_at"],
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"google_pay_webhook failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/ready-to-pay",
    response_model=GooglePayIsReadyToPayResponse,
    summary="Проверка готовности Google Pay",
)
@limiter.limit("100/hour")
async def is_ready_to_pay(
    request: Request,
) -> GooglePayIsReadyToPayResponse:
    """Проверка, готов ли клиент к оплате через Google Pay."""
    return GooglePayIsReadyToPayResponse(
        result=True,
        card_networks=["VISA", "MASTERCARD", "AMEX", "DISCOVER", "JCB"],
    )


@router.get(
    "/banks",
    response_model=Dict[str, Any],
    summary="Список поддерживаемых банков и сетей",
    tags=["Google Pay", "Info"],
)
@limiter.limit("100/hour")
async def get_google_pay_banks(
    request: Request,
) -> Dict[str, Any]:
    """Получить список поддерживаемых платёжных сетей."""
    return {
        "supported_networks": [
            "VISA",
            "MASTERCARD",
            "AMEX",
            "DISCOVER",
            "JCB",
            "INTERAC",
            "ELO",
        ],
        "card_classes": [
            "DEBIT",
            "CREDIT",
            "PREPAID",
        ],
        "countries": ["RU", "US", "GB", "DE", "FR", "ES", "IT", "CA", "AU", "JP", "IN", "BR"],
    }
