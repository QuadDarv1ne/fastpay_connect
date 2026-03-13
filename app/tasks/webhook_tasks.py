"""
Celery tasks для обработки webhook уведомлений с retry логикой.
"""

from typing import Any, Dict, Optional
import logging
from datetime import datetime, timezone

from celery import Celery, Task
from celery.exceptions import Retry

from app.database import SessionLocal
from app.repositories.payment_repository import PaymentRepository
from app.payment_gateways.yookassa import handle_yookassa_webhook
from app.payment_gateways.tinkoff import handle_tinkoff_webhook
from app.payment_gateways.cloudpayments import handle_cloudpayments_webhook
from app.payment_gateways.unitpay import handle_unitpay_webhook
from app.payment_gateways.robokassa import handle_robokassa_webhook

logger = logging.getLogger(__name__)

# Инициализация Celery
celery_app = Celery(
    'fastpay_connect',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/1',
    include=['app.tasks.webhook_tasks']
)

# Конфигурация Celery
celery_app.conf.update(
    # Retry настройки
    task_acks_late=True,
    task_reject_on_worker_or_loss=True,
    
    # Rate limiting
    task_default_rate_limit='100/m',
    
    # Таймауты
    task_soft_time_limit=300,
    task_time_limit=600,
    
    # Сериализация
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    
    # Тайзона
    timezone='UTC',
    enable_utc=True,
)


def get_db_session() -> SessionLocal:
    """Получение сессии БД для Celery задач."""
    return SessionLocal()


class DBTask(Task):
    """Базовый класс для задач с работой с БД."""
    
    _db = None
    
    @property
    def db(self) -> SessionLocal:
        if self._db is None:
            self._db = get_db_session()
        return self._db
    
    def after_return(self, *args, **kwargs) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None


celery_app.Task = DBTask


WEBHOOK_HANDLERS = {
    'yookassa': handle_yookassa_webhook,
    'tinkoff': handle_tinkoff_webhook,
    'cloudpayments': handle_cloudpayments_webhook,
    'unitpay': handle_unitpay_webhook,
    'robokassa': handle_robokassa_webhook,
}

STATUS_MAP = {
    "payment successful": "completed",
    "payment canceled": "cancelled",
    "payment failed": "failed",
    "payment refunded": "refunded",
}


def extract_webhook_event_id(payload: Dict[str, Any]) -> Optional[str]:
    """Извлечь event_id из webhook payload для идемпотентности."""
    return payload.get("event_id") or payload.get("id") or payload.get("transaction_id")


@celery_app.task(
    bind=True,
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,
)
def process_webhook_task(
    self,
    gateway: str,
    payload: Dict[str, Any],
    auth_value: str,
) -> Dict[str, Any]:
    """
    Обработка webhook уведомления через Celery с retry логикой.
    
    Args:
        gateway: Название платёжного шлюза (yookassa, tinkoff, etc.)
        payload: Данные webhook
        auth_value: Значение для аутентификации (сигнатура или токен)
    
    Returns:
        Результат обработки webhook
    """
    import asyncio
    from app.payment_gateways.yookassa import handle_yookassa_webhook
    from app.payment_gateways.tinkoff import handle_tinkoff_webhook
    from app.payment_gateways.cloudpayments import handle_cloudpayments_webhook
    from app.payment_gateways.unitpay import handle_unitpay_webhook
    from app.payment_gateways.robokassa import handle_robokassa_webhook
    
    # Импортируем хендлеры локально для избежания циклических импортов
    handlers = {
        'yookassa': handle_yookassa_webhook,
        'tinkoff': handle_tinkoff_webhook,
        'cloudpayments': handle_cloudpayments_webhook,
        'unitpay': handle_unitpay_webhook,
        'robokassa': handle_robokassa_webhook,
    }
    
    db = get_db_session()
    repository = PaymentRepository(db)
    
    try:
        handler = handlers.get(gateway)
        if not handler:
            logger.error(f"Unknown gateway: {gateway}")
            return {"status": "error", "message": f"Unknown gateway: {gateway}"}
        
        # Запускаем асинхронный хендлер в синхронном контексте Celery
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(handler(payload, auth_value))
        finally:
            loop.close()
        
        # Обновление статуса платежа
        order_id: Optional[str] = None
        if result.get("status") == "processed":
            order_id = payload.get("order_id") or payload.get("payment_id")
            if order_id:
                message = result.get("message", "").lower()
                db_status = STATUS_MAP.get(message, "pending")
                webhook_event_id = extract_webhook_event_id(payload)
                
                repository.update_status(
                    order_id=order_id,
                    status=db_status,
                    metadata=payload,
                    webhook_event_id=webhook_event_id,
                )
                logger.info(f"Payment {order_id} status updated to {db_status}")
        
        return {"status": "success", "message": result.get("message", ""), "order_id": order_id}
        
    except Exception as exc:
        # Логирование ошибки
        logger.error(f"Webhook processing error for {gateway}: {exc}")
        
        # Retry с экспоненциальной задержкой
        retry_count = self.request.retries
        max_retries = self.max_retries or 5
        
        if retry_count < max_retries:
            # Экспоненциальная задержка: 60s, 120s, 240s, 480s, 960s
            delay = 60 * (2 ** retry_count)
            logger.info(f"Retrying webhook processing in {delay}s (attempt {retry_count + 1}/{max_retries})")
            raise self.retry(exc=exc, countdown=delay)
        else:
            # Максимальное количество попыток исчерпано
            logger.error(f"Webhook processing failed after {max_retries} retries: {exc}")
            
            # Сохранение неудачного webhook в БД для последующего анализа
            try:
                order_id = payload.get("order_id") or payload.get("payment_id")
                if order_id:
                    repository.update_status(
                        order_id=order_id,
                        status="failed",
                        metadata={
                            **payload,
                            "webhook_error": str(exc),
                            "webhook_error_time": datetime.now(timezone.utc).isoformat(),
                            "retry_count": retry_count,
                        },
                    )
            except Exception as db_exc:
                logger.error(f"Failed to save webhook error to DB: {db_exc}")
            
            return {"status": "error", "message": f"Webhook processing failed: {exc}"}
    
    finally:
        db.close()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def send_webhook_retry_notification(
    self,
    gateway: str,
    payload: Dict[str, Any],
    error_message: str,
    retry_count: int,
) -> None:
    """
    Отправка уведомления о неудачной попытке обработки webhook.
    
    Эта задача может использоваться для отправки уведомлений
    администраторам или в мониторинг-системы.
    """
    logger.warning(
        f"Webhook retry notification: gateway={gateway}, "
        f"error={error_message}, retry_count={retry_count}"
    )
    # Здесь можно добавить отправку email, Slack notification, etc.


@celery_app.task(bind=True)
def cleanup_old_webhook_events(self, days: int = 30) -> int:
    """
    Очистка старых webhook событий.
    
    Args:
        days: Количество дней для хранения событий
    
    Returns:
        Количество удалённых записей
    """
    db = get_db_session()
    repository = PaymentRepository(db)
    
    try:
        # TODO: Реализовать метод очистки старых событий в репозитории
        logger.info(f"Cleanup old webhook events older than {days} days")
        return 0
    finally:
        db.close()


# Health check для Celery worker
@celery_app.task(bind=True)
def health_check(self) -> Dict[str, Any]:
    """Проверка работоспособности Celery worker."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "worker": self.request.hostname,
    }
