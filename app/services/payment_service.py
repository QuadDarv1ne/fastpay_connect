from sqlalchemy.orm import Session
from app.models.payment import Payment, PaymentStatus
from typing import Optional, Dict, Any
import json


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
    payment = Payment(
        order_id=order_id,
        payment_gateway=payment_gateway,
        amount=amount,
        currency=currency,
        description=description,
        payment_id=payment_id,
        payment_url=payment_url,
        status=PaymentStatus.PENDING.value,
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
) -> Optional[Payment]:
    """Обновляет статус платежа."""
    payment: Optional[Payment] = None
    if order_id:
        payment = db.query(Payment).filter(Payment.order_id == order_id).first()
    elif payment_id:
        payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()

    if not payment:
        return None

    payment.status = status
    if metadata:
        payment.metadata_json = json.dumps(metadata)

    db.commit()
    db.refresh(payment)
    return payment


def get_payment_by_order_id(db: Session, order_id: str) -> Optional[Payment]:
    """Получает платёж по order_id."""
    return db.query(Payment).filter(Payment.order_id == order_id).first()


def get_payment_by_id(db: Session, payment_id: str) -> Optional[Payment]:
    """Получает платёж по ID платёжной системы."""
    return db.query(Payment).filter(Payment.payment_id == payment_id).first()
