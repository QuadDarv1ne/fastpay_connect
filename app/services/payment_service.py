from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import func
from app.models.payment import Payment, PaymentStatus
from app.repositories.payment_repository import PaymentRepository
from app.schemas import PaymentRequest, PaymentResponse
from app.payment_gateways.yookassa import create_payment as yookassa_create
from app.payment_gateways.tinkoff import create_payment as tinkoff_create
from app.payment_gateways.cloudpayments import create_payment as cloudpayments_create
from app.payment_gateways.unitpay import create_payment as unitpay_create
from app.payment_gateways.robokassa import create_payment as robokassa_create
from app.payment_gateways.exceptions import (
    PaymentGatewayError,
    PaymentGatewayConfigError,
    PaymentGatewayTimeoutError,
    PaymentGatewayConnectionError,
)
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone
import json
import logging
import uuid

logger = logging.getLogger(__name__)


class PaymentServiceError(Exception):
    """Базовое исключение сервиса платежей."""

    def __init__(self, message: str, order_id: Optional[str] = None) -> None:
        super().__init__(message)
        self.order_id = order_id


class PaymentNotFoundError(PaymentServiceError):
    """Платёж не найден."""

    pass


class PaymentInvalidAmountError(PaymentServiceError):
    """Некорректная сумма платежа."""

    pass


GATEWAY_CONFIGS: Dict[str, Dict[str, Any]] = {
    "yookassa": {
        "name": "yookassa",
        "create_func": yookassa_create,
        "payment_id_field": "id",
        "payment_url_field": "confirmation.confirmation_url",
    },
    "tinkoff": {
        "name": "tinkoff",
        "create_func": tinkoff_create,
        "payment_id_field": "payment_id",
        "payment_url_field": "payment_url",
    },
    "cloudpayments": {
        "name": "cloudpayments",
        "create_func": cloudpayments_create,
        "payment_id_field": "transaction_id",
    },
    "unitpay": {
        "name": "unitpay",
        "create_func": unitpay_create,
        "payment_id_field": "payment_id",
    },
    "robokassa": {
        "name": "robokassa",
        "create_func": robokassa_create,
        "payment_id_field": "invoice_id",
    },
}


def _extract_nested_value(data: Dict[str, Any], path: str) -> Optional[Any]:
    """Extract a nested value from a dict by dot-separated path."""
    keys = path.split(".")
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value


def _generate_order_id() -> str:
    """Generate a unique order_id."""
    return str(uuid.uuid4())


class PaymentService:
    """Service for managing payments with business logic orchestration."""

    def __init__(self, repository: PaymentRepository) -> None:
        self.repository = repository

    async def create_payment(self, payment_data: PaymentRequest) -> PaymentResponse:
        """Create a new payment via the appropriate gateway.

        Determines the gateway from the payment_data (or defaults to yookassa),
        creates a DB record, calls the gateway, and returns a structured response.
        """
        gateway_key = getattr(payment_data, "gateway", None) or "yookassa"
        config = GATEWAY_CONFIGS.get(gateway_key)
        if not config:
            raise PaymentServiceError(f"Unknown payment gateway: {gateway_key}")

        order_id = payment_data.order_id or _generate_order_id()
        amount = payment_data.amount
        currency = payment_data.currency.value if hasattr(payment_data.currency, "value") else "RUB"
        description = payment_data.description

        # Create DB record
        self.repository.create(
            order_id=order_id,
            payment_gateway=gateway_key,
            amount=amount,
            description=description,
            currency=currency,
        )

        # Call the gateway
        create_func = config["create_func"]
        try:
            result = await create_func(amount, description, order_id)
        except PaymentGatewayConfigError as e:
            logger.error(f"Gateway config error: {e.message}")
            self.repository.update_status(
                order_id=order_id,
                status=PaymentStatus.FAILED,
                metadata={"error": e.message},
            )
            raise PaymentServiceError(
                "Payment gateway not configured", order_id=order_id
            ) from e
        except PaymentGatewayTimeoutError as e:
            logger.error(f"Gateway timeout: {e.message}")
            self.repository.update_status(
                order_id=order_id,
                status=PaymentStatus.FAILED,
                metadata={"error": "Gateway timeout"},
            )
            raise PaymentServiceError(
                "Payment gateway timeout", order_id=order_id
            ) from e
        except PaymentGatewayConnectionError as e:
            logger.error(f"Gateway connection error: {e.message}")
            self.repository.update_status(
                order_id=order_id,
                status=PaymentStatus.FAILED,
                metadata={"error": "Gateway connection failed"},
            )
            raise PaymentServiceError(
                "Payment gateway unavailable", order_id=order_id
            ) from e
        except PaymentGatewayError as e:
            logger.error(f"Gateway error: {e.message}")
            self.repository.update_status(
                order_id=order_id,
                status=PaymentStatus.FAILED,
                metadata={"error": e.message},
            )
            raise PaymentServiceError(e.message, order_id=order_id) from e

        if "error" in result:
            self.repository.update_status(
                order_id=order_id,
                status=PaymentStatus.FAILED,
                metadata={"error": result["error"]},
            )
            raise PaymentServiceError(result["error"], order_id=order_id)

        payment_id = result.get(config["payment_id_field"])
        payment_url = None
        if config.get("payment_url_field"):
            payment_url = _extract_nested_value(result, config["payment_url_field"])

        self.repository.update_status(
            order_id=order_id,
            status=PaymentStatus.PROCESSING,
            metadata={"payment_id": payment_id, "payment_url": payment_url},
        )

        return PaymentResponse(
            success=True,
            payment_id=payment_id,
            payment_url=payment_url,
            order_id=order_id,
            amount=amount,
            message="Платёж успешно создан",
        )


def create_payment_record(
    db: Session,
    order_id: str,
    payment_gateway: str,
    amount: float,
    description: str,
    currency: str = "RUB",
    payment_id: Optional[str] = None,
    payment_url: Optional[str] = None,
) -> Payment:
    """Создаёт запись о платеже в БД."""
    if amount <= 0:
        raise PaymentInvalidAmountError(f"Invalid amount: {amount}")

    payment = Payment(
        order_id=order_id,
        payment_gateway=payment_gateway,
        amount=amount,
        currency=currency,
        description=description,
        payment_id=payment_id,
        payment_url=payment_url,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def update_payment_status(
    db: Session,
    order_id: Optional[str] = None,
    payment_id: Optional[str] = None,
    status: str = PaymentStatus.COMPLETED.value,
    metadata: Optional[Dict[str, Any]] = None,
    webhook_event_id: Optional[str] = None,
) -> Optional[Payment]:
    """Обновляет статус платежа."""
    payment: Optional[Payment] = _get_payment(db, order_id, payment_id)

    if not payment:
        return None

    # Idempotency check for webhooks
    if webhook_event_id and payment.is_webhook_processed(webhook_event_id):
        logger.info(f"Webhook event {webhook_event_id} already processed for {payment.order_id}")
        return payment

    payment.status = status
    if metadata:
        payment.metadata_json = json.dumps(metadata)

    if webhook_event_id:
        payment.mark_webhook_processed(webhook_event_id)

    try:
        db.commit()
        db.refresh(payment)
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Database integrity error updating payment: {e}")
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error updating payment: {e}")
        raise

    return payment


def get_payment_by_order_id(db: Session, order_id: str) -> Optional[Payment]:
    """Получает платёж по order_id."""
    return _get_payment(db, order_id=order_id)


def get_payment_by_id(db: Session, payment_id: str) -> Optional[Payment]:
    """Получает платёж по ID платёжной системы."""
    return _get_payment(db, payment_id=payment_id)


def _get_payment(
    db: Session, order_id: Optional[str] = None, payment_id: Optional[str] = None
) -> Optional[Payment]:
    """Внутренняя функция для получения платежа."""
    if order_id:
        return db.query(Payment).filter(Payment.order_id == order_id).first()
    elif payment_id:
        return db.query(Payment).filter(Payment.payment_id == payment_id).first()
    return None


def get_payments_by_status(
    db: Session, status: Union[str, PaymentStatus], limit: int = 100
) -> List[Payment]:
    """Получает платежи по статусу."""
    status_value = status.value if isinstance(status, PaymentStatus) else status
    return (
        db.query(Payment)
        .filter(Payment.status == status_value)
        .order_by(Payment.created_at.desc())
        .limit(limit)
        .all()
    )


def get_payments_by_gateway(
    db: Session, gateway: str, limit: int = 100
) -> List[Payment]:
    """Получает платежи по платёжному шлюзу."""
    return (
        db.query(Payment)
        .filter(Payment.payment_gateway == gateway)
        .order_by(Payment.created_at.desc())
        .limit(limit)
        .all()
    )


def get_payments_by_date_range(
    db: Session,
    start_date: datetime,
    end_date: datetime,
    status: Optional[str] = None,
) -> List[Payment]:
    """Получает платежи за период."""
    query = db.query(Payment).filter(
        Payment.created_at >= start_date,
        Payment.created_at <= end_date,
    )

    if status:
        query = query.filter(Payment.status == status)

    return query.order_by(Payment.created_at.desc()).all()


def refund_payment(
    db: Session,
    order_id: Optional[str] = None,
    payment_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> Optional[Payment]:
    """Возврат платежа."""
    payment = _get_payment(db, order_id, payment_id)

    if not payment:
        logger.warning(f"Payment not found for refund: order_id={order_id}, payment_id={payment_id}")
        return None

    if payment.status == PaymentStatus.REFUNDED:
        logger.warning(f"Payment already refunded: {payment.order_id}")
        return payment

    if payment.status not in (PaymentStatus.COMPLETED, PaymentStatus.PROCESSING):
        logger.warning(f"Cannot refund payment in status {payment.status.value}: {payment.order_id}")
        return None

    payment.status = PaymentStatus.REFUNDED
    metadata = {"refund_reason": reason, "refunded_at": datetime.now(timezone.utc).isoformat()}
    if payment.metadata_json:
        existing = json.loads(payment.metadata_json)
        existing.update(metadata)
        payment.metadata_json = json.dumps(existing)
    else:
        payment.metadata_json = json.dumps(metadata)

    db.commit()
    db.refresh(payment)
    logger.info(f"Payment refunded: {payment.order_id}")
    return payment


def cancel_payment(
    db: Session,
    order_id: Optional[str] = None,
    payment_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> Optional[Payment]:
    """Отмена платежа."""
    payment = _get_payment(db, order_id, payment_id)

    if not payment:
        logger.warning(f"Payment not found for cancel: order_id={order_id}, payment_id={payment_id}")
        return None

    if payment.status in (PaymentStatus.COMPLETED, PaymentStatus.REFUNDED):
        logger.warning(f"Cannot cancel payment in status {payment.status.value}: {payment.order_id}")
        return payment

    if payment.status == PaymentStatus.CANCELLED:
        logger.warning(f"Payment already cancelled: {payment.order_id}")
        return payment

    payment.status = PaymentStatus.CANCELLED
    metadata = {"cancel_reason": reason, "cancelled_at": datetime.now(timezone.utc).isoformat()}
    if payment.metadata_json:
        existing = json.loads(payment.metadata_json)
        existing.update(metadata)
        payment.metadata_json = json.dumps(existing)
    else:
        payment.metadata_json = json.dumps(metadata)

    db.commit()
    db.refresh(payment)
    logger.info(f"Payment cancelled: {payment.order_id}")
    return payment


def get_payment_statistics(db: Session) -> Dict[str, Any]:
    """Получает статистику по платежам."""
    total = db.query(Payment).count()
    by_status = (
        db.query(Payment.status, func.count(Payment.id))
        .group_by(Payment.status)
        .all()
    )
    by_gateway = (
        db.query(Payment.payment_gateway, func.count(Payment.id))
        .group_by(Payment.payment_gateway)
        .all()
    )
    total_amount = db.query(func.sum(Payment.amount)).filter(
        Payment.status == PaymentStatus.COMPLETED
    ).scalar() or 0

    return {
        "total_payments": total,
        "by_status": dict(by_status),
        "by_gateway": dict(by_gateway),
        "total_completed_amount": float(total_amount),
    }
