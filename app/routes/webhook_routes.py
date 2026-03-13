from typing import Any, Callable, Dict, List, Optional, Tuple
from fastapi import APIRouter, HTTPException, Request, Depends, status
from app.payment_gateways.yookassa import handle_yookassa_webhook
from app.payment_gateways.tinkoff import handle_tinkoff_webhook
from app.payment_gateways.cloudpayments import handle_cloudpayments_webhook
from app.payment_gateways.unitpay import handle_unitpay_webhook
from app.payment_gateways.robokassa import handle_robokassa_webhook
from app.database import get_db
from app.repositories.payment_repository import PaymentRepository
from app.dependencies import get_payment_repository
from app.utils.ip_validator import verify_webhook_ip
from app.settings import settings
from app.tasks.webhook_tasks import process_webhook_task
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


def _extract_webhook_event_id(payload: Dict[str, Any]) -> Optional[str]:
    """Извлечь event_id из webhook payload для идемпотентности."""
    return payload.get("event_id") or payload.get("id") or payload.get("transaction_id")


async def process_webhook(
    config: WebhookConfig,
    payload: Dict[str, Any],
    auth_value: str,
    repository: PaymentRepository,
    use_celery: Optional[bool] = None,
) -> Tuple[Dict[str, str], Optional[str]]:
    """Обработка webhook уведомления."""
    # Проверяем переменную окружения для тестов
    if use_celery is None:
        import os
        use_celery = os.getenv("DISABLE_CELERY", "false").lower() != "true"
    
    if use_celery and settings.celery_enabled:
        # Асинхронная обработка через Celery с retry логикой
        task = process_webhook_task.delay(
            gateway=config.name,
            payload=payload,
            auth_value=auth_value,
        )
        logger.info(f"Webhook queued to Celery: task_id={task.id}")
        return {"status": "queued", "message": "Webhook queued for processing"}, None

    # Синхронная обработка (fallback)
    try:
        result = await config.handler(payload, auth_value)
    except Exception as e:
        logger.error(f"Webhook handler error: {e}")
        raise HTTPException(
            status_code=400, detail=f"Webhook processing failed: {e}"
        ) from e

    order_id: Optional[str] = None
    if result.get("status") == "processed":
        order_id = payload.get("order_id") or payload.get("payment_id")
        if order_id:
            message = result.get("message", "").lower()
            db_status = STATUS_MAP.get(message, "pending")
            webhook_event_id = _extract_webhook_event_id(payload)
            repository.update_status(
                order_id=order_id,
                status=db_status,
                metadata=payload,
                webhook_event_id=webhook_event_id,
            )
            logger.info(f"Payment {order_id} status updated to {db_status}")

    return result, order_id


def create_webhook_endpoint(webhook_key: str):
    """Создание endpoint для webhook."""
    config = WEBHOOKS[webhook_key]

    async def handler(
        request: Request,
        repository: PaymentRepository = Depends(get_payment_repository),
    ) -> Dict[str, Any]:
        await verify_webhook_ip(request, config.ip_whitelist)
        payload = await request.json()

        if config.token_field:
            auth_value = payload.get(
                config.token_field, request.headers.get(config.signature_header, "")
            )
        else:
            auth_value = request.headers.get(config.signature_header, "")

        result, _ = await process_webhook(config, payload, auth_value, repository)
        return {"status": "success", "message": result.get("message", "")}

    return handler


router.post("/yookassa")(create_webhook_endpoint("yookassa"))
router.post("/tinkoff")(create_webhook_endpoint("tinkoff"))
router.post("/cloudpayments")(create_webhook_endpoint("cloudpayments"))
router.post("/unitpay")(create_webhook_endpoint("unitpay"))
router.post("/robokassa")(create_webhook_endpoint("robokassa"))
