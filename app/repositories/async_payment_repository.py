"""Асинхронный репозиторий для работы с платежами.

Использует SQLAlchemy 2.0 async для неблокирующей работы с БД.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment, PaymentStatus
from app.utils.tenant import get_current_tenant

logger = logging.getLogger(__name__)


class AsyncPaymentRepository:
    """Асинхронный репозиторий для операций с платежами.

    Пример использования:
        async with AsyncSessionLocal() as session:
            repo = AsyncPaymentRepository(session)
            payment = await repo.create(
                order_id="order_123",
                payment_gateway="yookassa",
                amount=1000.0,
                description="Test payment"
            )
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(
        self,
        order_id: str,
        payment_gateway: str,
        amount: float,
        description: str,
        currency: str = "RUB",
        payment_id: Optional[str] = None,
        payment_url: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> Payment:
        """Создать платёж.

        Args:
            order_id: Уникальный идентификатор заказа
            payment_gateway: Название платёжного шлюза
            amount: Сумма платежа
            description: Описание платежа
            currency: Валюта платежа
            payment_id: ID платежа в шлюзе
            payment_url: URL для оплаты
            tenant_id: ID тенанта

        Returns:
            Созданный объект Payment

        Raises:
            ValueError: Если сумма <= 0
            IntegrityError: Если order_id уже существует
        """
        if amount <= 0:
            raise ValueError(f"Invalid amount: {amount}")

        if tenant_id is None:
            current_tenant = get_current_tenant()
            if current_tenant:
                tenant_id = current_tenant.id

        payment = Payment(
            order_id=order_id,
            payment_gateway=payment_gateway,
            amount=amount,
            currency=currency,
            description=description,
            payment_id=payment_id,
            payment_url=payment_url,
            status=PaymentStatus.PENDING,
            tenant_id=tenant_id,
        )

        self._db.add(payment)
        await self._db.commit()
        await self._db.refresh(payment)
        return payment

    async def get_by_order_id(
        self, order_id: str, tenant_id: Optional[int] = None
    ) -> Optional[Payment]:
        """Получить платёж по order_id."""
        if tenant_id is None:
            current_tenant = get_current_tenant()
            if current_tenant:
                tenant_id = current_tenant.id

        stmt = select(Payment).where(Payment.order_id == order_id)

        if tenant_id:
            stmt = stmt.where(Payment.tenant_id == tenant_id)

        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id(self, payment_id: int) -> Optional[Payment]:
        """Получить платёж по ID."""
        stmt = select(Payment).where(Payment.id == payment_id)
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_payment_id(
        self, payment_id: str, gateway: Optional[str] = None
    ) -> Optional[Payment]:
        """Получить платёж по payment_id (ID в шлюзе)."""
        stmt = select(Payment).where(Payment.payment_id == payment_id)

        if gateway:
            stmt = stmt.where(Payment.payment_gateway == gateway)

        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_status(
        self, status: PaymentStatus, limit: int = 100
    ) -> List[Payment]:
        """Получить платежи по статусу."""
        stmt = select(Payment).where(Payment.status == status).limit(limit)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self, payment: Payment, status: PaymentStatus
    ) -> Payment:
        """Обновить статус платежа."""
        payment.status = status
        payment.updated_at = datetime.now(timezone.utc)
        await self._db.commit()
        await self._db.refresh(payment)
        return payment

    async def update_metadata(
        self, payment: Payment, metadata: Dict[str, Any]
    ) -> Payment:
        """Обновить метаданные платежа."""
        payment.metadata_json = json.dumps(metadata)
        payment.updated_at = datetime.now(timezone.utc)
        await self._db.commit()
        await self._db.refresh(payment)
        return payment

    async def mark_webhook_processed(
        self, payment: Payment, event_id: str
    ) -> Payment:
        """Отметить webhook событие как обработанное."""
        payment.mark_webhook_processed(event_id)
        payment.updated_at = datetime.now(timezone.utc)
        await self._db.commit()
        await self._db.refresh(payment)
        return payment

    async def get_pending_payments(
        self, older_than: Optional[timedelta] = None
    ) -> List[Payment]:
        """Получить ожидающие платежи.

        Args:
            older_than: Найти платежи старше указанного времени

        Returns:
            Список pending платежей
        """
        stmt = select(Payment).where(Payment.status == PaymentStatus.PENDING)

        if older_than:
            cutoff_time = datetime.now(timezone.utc) - older_than
            stmt = stmt.where(Payment.created_at < cutoff_time)

        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tenant_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Получить статистику платежей.

        Returns:
            Dict с ключами: total_count, total_amount, by_status, by_gateway
        """
        # Базовый запрос
        base_query = select(Payment)

        if start_date:
            base_query = base_query.where(Payment.created_at >= start_date)
        if end_date:
            base_query = base_query.where(Payment.created_at <= end_date)
        if tenant_id:
            base_query = base_query.where(Payment.tenant_id == tenant_id)

        # Общая статистика
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_stmt = select(func.sum(Payment.amount)).select_from(
            base_query.subquery()
        )

        count_result = await self._db.execute(count_stmt)
        total_result = await self._db.execute(total_stmt)

        total_count = count_result.scalar() or 0
        total_amount = total_result.scalar() or 0.0

        # Статистика по статусам
        status_stmt = select(
            Payment.status, func.count(Payment.id), func.sum(Payment.amount)
        )
        if start_date:
            status_stmt = status_stmt.where(Payment.created_at >= start_date)
        if end_date:
            status_stmt = status_stmt.where(Payment.created_at <= end_date)
        if tenant_id:
            status_stmt = status_stmt.where(Payment.tenant_id == tenant_id)

        status_stmt = status_stmt.group_by(Payment.status)
        status_result = await self._db.execute(status_stmt)

        by_status = {
            status.value: {"count": count, "amount": amount or 0.0}
            for status, count, amount in status_result.all()
        }

        # Статистика по шлюзам
        gateway_stmt = select(
            Payment.payment_gateway, func.count(Payment.id), func.sum(Payment.amount)
        )
        if start_date:
            gateway_stmt = gateway_stmt.where(Payment.created_at >= start_date)
        if end_date:
            gateway_stmt = gateway_stmt.where(Payment.created_at <= end_date)
        if tenant_id:
            gateway_stmt = gateway_stmt.where(Payment.tenant_id == tenant_id)

        gateway_stmt = gateway_stmt.group_by(Payment.payment_gateway)
        gateway_result = await self._db.execute(gateway_stmt)

        by_gateway = {
            gateway: {"count": count, "amount": amount or 0.0}
            for gateway, count, amount in gateway_result.all()
        }

        return {
            "total_count": total_count,
            "total_amount": total_amount,
            "by_status": by_status,
            "by_gateway": by_gateway,
        }

    async def delete(self, payment: Payment) -> None:
        """Удалить платёж."""
        await self._db.delete(payment)
        await self._db.commit()

    async def cleanup_old_payments(
        self, older_than_days: int = 90
    ) -> int:
        """Очистить старые платежи.

        Args:
            older_than_days: Удалять платежи старше N дней

        Returns:
            Количество удалённых записей
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=older_than_days)

        stmt = delete(Payment).where(
            Payment.status.in_([PaymentStatus.CANCELLED, PaymentStatus.FAILED]),
            Payment.created_at < cutoff_date,
        )

        result = await self._db.execute(stmt)
        await self._db.commit()

        deleted_count = result.rowcount
        logger.info(f"Deleted {deleted_count} old payments")

        return deleted_count
