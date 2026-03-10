from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import func
from app.models.payment import Payment, PaymentStatus
from typing import Optional, Dict, Any, List, Union
from datetime import datetime, timezone
import json
import logging

logger = logging.getLogger(__name__)


class PaymentServiceError(Exception):
    """Базовое исключение сервиса платежей."""

    pass


class PaymentNotFoundError(PaymentServiceError):
    """Платёж не найден."""

    pass


class PaymentInvalidAmountError(PaymentServiceError):
    """Некорректная сумма платежа."""

    pass


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
