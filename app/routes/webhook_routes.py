from typing import Any, Callable, Dict, List, Optional, Tuple
from fastapi import APIRouter, HTTPException, Request, Depends, status
from sqlalchemy.orm import Session

from app.payment_gateways.yookassa import handle_yookassa_webhook
from app.payment_gateways.tinkoff import handle_tinkoff_webhook
from app.payment_gateways.cloudpayments import handle_cloudpayments_webhook
from app.payment_gateways.unitpay import handle_unitpay_webhook
from app.payment_gateways.robokassa import handle_robokassa_webhook
from app.database import get_db
from app.services.payment_service import update_payment_status, get_payment_by_order_id
from app.utils.ip_validator import verify_webhook_ip
from app.settings import settings

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

router = APIRouter()


@dataclass
class WebhookConfig:
    """Конфигурация webhook."""

    name: str
    handler: Callable
    ip_whitelist: List[str]
    signature_header: str = "X-Signature"
    token_field: Optional[str] = None


WEBHOOKS: Dict[str, WebhookConfig] = {
    "yookassa": WebhookConfig(
        name="yookassa",
        handler=handle_yookassa_webhook,
        ip_whitelist=settings.yookassa_ips,
    ),
    "tinkoff": WebhookConfig(
        name="tinkoff",
        handler=handle_tinkoff_webhook,
        ip_whitelist=settings.tinkoff_ips,
    ),
    "cloudpayments": WebhookConfig(
        name="cloudpayments",
        handler=handle_cloudpayments_webhook,
        ip_whitelist=settings.cloudpayments_ips,
        token_field="token",
    ),
    "unitpay": WebhookConfig(
        name="unitpay",
        handler=handle_unitpay_webhook,
        ip_whitelist=settings.unitpay_ips,
    ),
    "robokassa": WebhookConfig(
        name="robokassa",
        handler=handle_robokassa_webhook,
        ip_whitelist=settings.robokassa_ips,
    ),
}

STATUS_MAP: Dict[str, str] = {
    "payment successful": "completed",
    "payment canceled": "cancelled",
    "payment failed": "failed",
    "payment refunded": "refunded",
}


async def process_webhook(
    config: WebhookConfig,
    payload: Dict[str, Any],
    auth_value: str,
    db: Session,
) -> Tuple[Dict[str, str], Optional[str]]:
    """Обработка webhook уведомления с поддержкой идемпотентности.

    Args:
        config: Конфигурация webhook.
        payload: Тело webhook.
        auth_value: Значение для аутентификации (подпись или токен).
        db: Сессия БД.

    Returns:
        Кортеж (результат обработки, order_id).

    Raises:
        HTTPException: Ошибка обработки webhook.
    """
    try:
        result = await config.handler(payload, auth_value)
    except Exception as e:
        logger.exception(f"Webhook handler error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook processing failed: {e}",
        ) from e

    order_id: Optional[str] = None
    if result.get("status") == "processed":
        order_id = payload.get("order_id") or payload.get("payment_id")
        if order_id:
            message = result.get("message", "").lower()
            db_status = STATUS_MAP.get(message, "pending")

            # Извлекаем ID транзакции и события для идемпотентности
            transaction_id = payload.get("transaction_id")
            # Используем комбинацию event_id и timestamp для уникальности
            webhook_event_id = (
                payload.get("event_id") or
                payload.get("id") or
                payload.get("payment_id") or
                payload.get("order_id") or
                f"{payload.get('event', '')}_{payload.get('created_at', '')}"
            )

            # Обновляем статус с проверкой идемпотентности
            payment = update_payment_status(
                db=db,
                order_id=order_id,
                transaction_id=transaction_id,
                status=db_status,
                metadata=payload,
                webhook_event_id=webhook_event_id,
            )

            if payment:
                logger.info(
                    f"Payment {order_id} status updated to {db_status} "
                    f"(event_id: {webhook_event_id})"
                )
            else:
                logger.warning(f"Payment {order_id} not found for webhook update")

    return result, order_id


def create_webhook_endpoint(webhook_key: str):
    """Создание endpoint для webhook.

    Args:
        webhook_key: Ключ шлюза из WEBHOOKS.

    Returns:
        Async handler function.
    """
    config = WEBHOOKS[webhook_key]

    async def handler(
        request: Request,
        db: Session = Depends(get_db),
    ) -> Dict[str, Any]:
        # Проверка IP адреса
        await verify_webhook_ip(request, config.ip_whitelist)

        # Парсинг payload
        try:
            payload = await request.json()
        except Exception as e:
            logger.error(f"Failed to parse webhook payload: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON payload",
            ) from e

        # Получение значения для аутентификации
        if config.token_field:
            auth_value = payload.get(
                config.token_field,
                request.headers.get(config.signature_header, ""),
            )
        else:
            auth_value = request.headers.get(config.signature_header, "")

        # Обработка webhook
        result, _ = await process_webhook(config, payload, auth_value, db)

        return {"status": "success", "message": result.get("message", "")}

    return handler


# Регистрация webhook endpoints
router.post("/yookassa")(create_webhook_endpoint("yookassa"))
router.post("/tinkoff")(create_webhook_endpoint("tinkoff"))
router.post("/cloudpayments")(create_webhook_endpoint("cloudpayments"))
router.post("/unitpay")(create_webhook_endpoint("unitpay"))
router.post("/robokassa")(create_webhook_endpoint("robokassa"))
