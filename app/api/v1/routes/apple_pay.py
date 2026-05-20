"""Apple Pay API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.middleware.rate_limiter import limiter
from app.schemas.apple_pay import (
    ApplePayPaymentRequest,
    ApplePayPaymentResponse,
    ApplePayPaymentInfoResponse,
    ApplePayPaymentSessionRequest,
    ApplePayTokenRequest,
    ApplePayRefundRequest,
    ApplePayRefundResponse,
    ApplePayWebhookPayload,
    ApplePayWebhookResponse,
    ApplePayMerchantValidationRequest,
    ApplePayMerchantValidationResponse,
    ApplePayStatusEnum,
)

router = APIRouter(prefix="/apple-pay", tags=["Apple Pay"])


@router.post(
    "/payment/session",
    response_model=ApplePayPaymentResponse,
    summary="Создание сессии Apple Pay"
)
@limiter.limit("50/hour")
async def create_apple_pay_session(
    request: Request,
    payment_data: ApplePayPaymentSessionRequest,
) -> ApplePayPaymentResponse:
    """Создание сессии Apple Pay для оплаты.

    Создаёт платёжную сессию с генерацией session_data для инициализации
    Apple Pay на клиентской стороне.

    **Требуется:**
    - Настроенный Apple Merchant ID
    - SSL сертификат для домена

    **Пример использования на клиенте:**
    ```javascript
    const session = new ApplePaySession(3, sessionData);
    session.begin();
    ```
    """
    from app.payment_gateways.apple_pay import get_gateway
    from app.payment_gateways.exceptions import PaymentGatewayError

    try:
        gateway = get_gateway()
        result = await gateway.create_payment_session(
            amount=payment_data.amount,
            order_id=payment_data.order_id,
            description=payment_data.description,
            currency=payment_data.currency,
            country_code="RU",
        )

        return ApplePayPaymentResponse(
            success=True,
            payment_id=result.get("payment_id", ""),
            order_id=result["order_id"],
            amount=result["amount"],
            currency=result["currency"],
            status=ApplePayStatusEnum.PENDING,
            session_data=result.get("session_data"),
            merchant_id=result.get("merchant_id"),
            message="Payment session created successfully",
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/payment",
    response_model=ApplePayPaymentResponse,
    summary="Создание платежа Apple Pay"
)
@limiter.limit("50/hour")
async def create_apple_pay_payment(
    request: Request,
    payment_data: ApplePayPaymentRequest,
) -> ApplePayPaymentResponse:
    """Создание платежа через Apple Pay.

    Создаёт платёж с подготовкой данных для Apple Pay SDK.
    """
    from app.payment_gateways.apple_pay import get_gateway
    from app.payment_gateways.exceptions import PaymentGatewayError

    try:
        gateway = get_gateway()
        result = await gateway.create_payment(
            amount=payment_data.amount,
            order_id=payment_data.order_id,
            description=payment_data.description or f"Order {payment_data.order_id}",
            currency=payment_data.currency,
            country_code=payment_data.country_code,
            supported_networks=(
                [n.value for n in payment_data.supported_networks]
                if payment_data.supported_networks else None
            ),
        )

        return ApplePayPaymentResponse(
            success=True,
            order_id=result["order_id"],
            amount=result["amount"],
            currency=result["currency"],
            status=ApplePayStatusEnum.PENDING,
            session_data=result.get("session_data"),
            merchant_id=result.get("merchant_id"),
            message="Payment created successfully",
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/payment/process-token",
    response_model=ApplePayPaymentResponse,
    summary="Обработка токена Apple Pay"
)
@limiter.limit("30/hour")
async def process_apple_pay_token(
    request: Request,
    token_data: ApplePayTokenRequest,
) -> ApplePayPaymentResponse:
    """Обработка токена Apple Pay после авторизации пользователем.

    Принимает токен от Apple Pay и создаёт платёж в процессинговой системе.
    """
    from app.payment_gateways.apple_pay import get_gateway
    from app.payment_gateways.exceptions import PaymentGatewayError

    try:
        gateway = get_gateway()
        result = await gateway.process_payment_token(
            token_data=token_data.token_data,
            order_id=token_data.order_id,
            amount=token_data.amount,
            currency=token_data.currency,
        )

        return ApplePayPaymentResponse(
            success=True,
            payment_id=result["payment_id"],
            order_id=result["order_id"],
            amount=result["amount"],
            currency=result["currency"],
            status=ApplePayStatusEnum.COMPLETED,
            message="Payment processed successfully",
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get(
    "/payment/{payment_id}",
    response_model=ApplePayPaymentInfoResponse,
    summary="Информация о платеже Apple Pay"
)
@limiter.limit("100/hour")
async def get_apple_pay_payment(
    request: Request,
    payment_id: str,
) -> ApplePayPaymentInfoResponse:
    """Получение информации о платеже Apple Pay."""
    # В реальной реализации здесь был бы запрос к базе данных или API
    # Для примера возвращаем заглушку

    return ApplePayPaymentInfoResponse(
        payment_id=payment_id,
        order_id=f"order_{payment_id}",
        amount=1000.0,
        currency="RUB",
        status=ApplePayStatusEnum.COMPLETED,
        card_network="visa",
        transaction_id=f"txn_{payment_id}",
        created_at=datetime.now(timezone.utc).isoformat(),
        processed_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post(
    "/payment/{payment_id}/refund",
    response_model=ApplePayRefundResponse,
    summary="Возврат платежа Apple Pay"
)
@limiter.limit("20/hour")
async def refund_apple_pay_payment(
    request: Request,
    payment_id: str,
    refund_data: ApplePayRefundRequest,
) -> ApplePayRefundResponse:
    """Возврат платежа Apple Pay.

    Создаёт возврат полного или частичного платежа.
    """
    from app.payment_gateways.apple_pay import get_gateway
    from app.payment_gateways.exceptions import PaymentGatewayError

    try:
        gateway = get_gateway()
        # В реальной реализации здесь вызывается API для refund

        refund_id = f"ref_{payment_id}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        amount = refund_data.amount or 1000.0  # Полная сумма по умолчанию

        return ApplePayRefundResponse(
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
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/merchant/validate",
    response_model=ApplePayMerchantValidationResponse,
    summary="Валидация мерчанта Apple Pay"
)
@limiter.limit("10/hour")
async def validate_apple_pay_merchant(
    request: Request,
    validation_data: ApplePayMerchantValidationRequest,
) -> ApplePayMerchantValidationResponse:
    """Валидация мерчанта для Apple Pay.

    Проверяет домен и возвращает данные для инициализации Apple Pay сессии.
    Требуется для первого запуска Apple Pay на домене.
    """
    from app.payment_gateways.apple_pay import get_gateway
    from app.payment_gateways.exceptions import PaymentGatewayError

    try:
        gateway = get_gateway()
        result = await gateway.validate_merchant(
            domain_name=validation_data.domain_name
        )

        return ApplePayMerchantValidationResponse(
            merchant_id=result["merchant_id"],
            domain_name=result["domain_name"],
            environment=result["environment"],
            status=result["status"],
            expires_at=result["expires_at"],
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post(
    "/webhook",
    response_model=ApplePayWebhookResponse,
    summary="Webhook для уведомлений Apple Pay",
    include_in_schema=False  # Скрыто из Swagger, т.к. webhook не отправляется напрямую
)
async def apple_pay_webhook(
    request: Request,
    payload: ApplePayWebhookPayload,
) -> ApplePayWebhookResponse:
    """Обработка webhook уведомлений от Apple Pay.

    Apple Pay не отправляет webhook напрямую, но процессинговый банк
    может отправлять уведомления о статусе платежей.
    """
    from app.payment_gateways.apple_pay import get_gateway
    from app.payment_gateways.exceptions import PaymentGatewayError

    try:
        gateway = get_gateway()

        # Преобразуем в dict для обработки
        payload_dict = payload.model_dump()
        result = await gateway.handle_webhook(payload=payload_dict)

        return ApplePayWebhookResponse(
            status=result["status"],
            order_id=result["order_id"],
            event_type=result["event_type"],
            processed_at=result["processed_at"],
        )

    except PaymentGatewayError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get(
    "/banks",
    response_model=Dict[str, Any],
    summary="Список поддерживаемых банков и сетей",
    tags=["Apple Pay", "Info"]
)
@limiter.limit("100/hour")
async def get_apple_pay_banks(
    request: Request,
) -> Dict[str, Any]:
    """Получить список поддерживаемых платёжных сетей."""
    return {
        "supported_networks": [
            "visa",
            "masterCard",
            "amex",
            "discover",
            "elo",
            "jcb",
            "cartesBancaires",
            "interac",
        ],
        "merchant_capabilities": [
            "supports3DS",
            "supportsCredit",
            "supportsDebit",
            "supportsPrepaid",
        ],
        "countries": ["RU", "US", "GB", "DE", "FR", "ES", "IT", "CA", "AU", "JP"],
    }
