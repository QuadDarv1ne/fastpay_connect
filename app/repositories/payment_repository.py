"""Репозиторий для работы с платежами."""

import json
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.models.payment import Payment, PaymentStatus


class RepositoryError(Exception):
    """Базовое исключение репозитория."""

    pass


class PaymentNotFoundError(RepositoryError):
    """Платёж не найден."""

    pass


class PaymentRepository:
    """Репозиторий для операций с платежами."""

    def __init__(self, db: Session):
        self._db = db

    def create(
        self,
        order_id: str,
        payment_gateway: str,
        amount: float,
        description: str,
        currency: str = "RUB",
        payment_id: Optional[str] = None,
        payment_url: Optional[str] = None,
    ) -> Payment:
        """Создать платёж."""
        if amount <= 0:
            raise ValueError(f"Invalid amount: {amount}")

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
        self._db.add(payment)
        self._db.commit()
        self._db.refresh(payment)
        return payment

    def get_by_order_id(self, order_id: str) -> Optional[Payment]:
        """Получить платёж по order_id."""
        return self._db.query(Payment).filter(Payment.order_id == order_id).first()

    def get_by_payment_id(self, payment_id: str) -> Optional[Payment]:
        """Получить платёж по payment_id."""
        return self._db.query(Payment).filter(Payment.payment_id == payment_id).first()

    def get_by_transaction_id(self, transaction_id: str) -> Optional[Payment]:
        """Получить платёж по transaction_id."""
        return self._db.query(Payment).filter(Payment.transaction_id == transaction_id).first()

    def update_status(
        self,
        order_id: Optional[str] = None,
        payment_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        status: Union[str, PaymentStatus] = PaymentStatus.COMPLETED,
        metadata: Optional[Dict[str, Any]] = None,
        webhook_event_id: Optional[str] = None,
    ) -> Optional[Payment]:
        """Обновить статус платежа."""
        payment = self._get_by_any(order_id, payment_id, transaction_id)
        if not payment:
            return None

        status_value = status.value if isinstance(status, PaymentStatus) else status

        if webhook_event_id:
            if payment.is_webhook_processed(webhook_event_id):
                return payment
            payment.mark_webhook_processed(webhook_event_id)

        if transaction_id and not payment.transaction_id:
            payment.transaction_id = transaction_id

        payment.status = status_value
        if metadata:
            payment.metadata_json = json.dumps(metadata)

        try:
            self._db.commit()
            self._db.refresh(payment)
        except IntegrityError as e:
            self._db.rollback()
            raise RepositoryError(f"Database integrity error: {e}") from e
        except SQLAlchemyError as e:
            self._db.rollback()
            raise RepositoryError(f"Database error: {e}") from e

        return payment

    def get_by_status(
        self, status: Union[str, PaymentStatus], limit: int = 100
    ) -> List[Payment]:
        """Получить платежи по статусу."""
        status_value = status.value if isinstance(status, PaymentStatus) else status
        return (
            self._db.query(Payment)
            .filter(Payment.status == status_value)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_status_paginated(
        self, status: Union[str, PaymentStatus], page: int = 1, page_size: int = 20
    ) -> tuple[List[Payment], int]:
        """Получить платежи по статусу с пагинацией."""
        status_value = status.value if isinstance(status, PaymentStatus) else status
        total = self._db.query(Payment).filter(Payment.status == status_value).count()
        offset = (page - 1) * page_size
        payments = (
            self._db.query(Payment)
            .filter(Payment.status == status_value)
            .order_by(Payment.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return payments, total

    def get_by_gateway(self, gateway: str, limit: int = 100) -> List[Payment]:
        """Получить платежи по шлюзу."""
        return (
            self._db.query(Payment)
            .filter(Payment.payment_gateway == gateway)
            .order_by(Payment.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_gateway_paginated(
        self, gateway: str, page: int = 1, page_size: int = 20
    ) -> tuple[List[Payment], int]:
        """Получить платежи по шлюзу с пагинацией."""
        total = self._db.query(Payment).filter(Payment.payment_gateway == gateway).count()
        offset = (page - 1) * page_size
        payments = (
            self._db.query(Payment)
            .filter(Payment.payment_gateway == gateway)
            .order_by(Payment.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return payments, total

    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        status: Optional[Union[str, PaymentStatus]] = None,
    ) -> List[Payment]:
        """Получить платежи за период."""
        query = self._db.query(Payment).filter(
            Payment.created_at >= start_date,
            Payment.created_at <= end_date,
        )
        if status:
            status_value = status.value if isinstance(status, PaymentStatus) else status
            query = query.filter(Payment.status == status_value)
        return query.order_by(Payment.created_at.desc()).all()

    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику."""
        total = self._db.query(Payment).count()
        by_status = (
            self._db.query(Payment.status, func.count(Payment.id))
            .group_by(Payment.status)
            .all()
        )
        by_gateway = (
            self._db.query(Payment.payment_gateway, func.count(Payment.id))
            .group_by(Payment.payment_gateway)
            .all()
        )
        total_amount = (
            self._db.query(func.sum(Payment.amount))
            .filter(Payment.status == PaymentStatus.COMPLETED)
            .scalar()
            or 0
        )

        return {
            "total_payments": total,
            "by_status": dict(by_status),
            "by_gateway": dict(by_gateway),
            "total_completed_amount": float(total_amount),
        }

    def invalidate_statistics_cache(self) -> None:
        """Инвалидировать кэш статистики."""
        pass

    def _get_by_any(
        self,
        order_id: Optional[str] = None,
        payment_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
    ) -> Optional[Payment]:
        """Внутренний метод для получения платежа."""
        if order_id:
            return self.get_by_order_id(order_id)
        elif payment_id:
            return self.get_by_payment_id(payment_id)
        elif transaction_id:
            return self.get_by_transaction_id(transaction_id)
        return None
