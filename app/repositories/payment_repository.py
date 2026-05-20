"""Репозиторий для работы с платежами."""

import json
import logging
from typing import List, Optional, Dict, Any, Union, Tuple
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.models.payment import Payment, PaymentStatus
from app.utils.tenant import get_current_tenant

logger = logging.getLogger(__name__)


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

    @property
    def db(self) -> Session:
        return self._db

    def create(
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
        """Создать платёж."""
        if amount <= 0:
            raise ValueError(f"Invalid amount: {amount}")

        # Если tenant_id не указан, пробуем получить из контекста
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
        self._db.commit()
        self._db.refresh(payment)
        return payment

    def get_by_order_id(self, order_id: str, tenant_id: Optional[int] = None) -> Optional[Payment]:
        """Получить платёж по order_id."""
        query = self._db.query(Payment).filter(Payment.order_id == order_id)
        
        # Если tenant_id не указан, используем текущий из контекста
        if tenant_id is None:
            current_tenant = get_current_tenant()
            if current_tenant:
                tenant_id = current_tenant.id
        
        # Фильтруем по tenant если он указан
        if tenant_id is not None:
            query = query.filter(Payment.tenant_id == tenant_id)
            
        return query.first()

    def get_by_payment_id(self, payment_id: str, tenant_id: Optional[int] = None) -> Optional[Payment]:
        """Получить платёж по payment_id."""
        query = self._db.query(Payment).filter(Payment.payment_id == payment_id)
        
        if tenant_id is None:
            current_tenant = get_current_tenant()
            if current_tenant:
                tenant_id = current_tenant.id
        
        if tenant_id is not None:
            query = query.filter(Payment.tenant_id == tenant_id)
            
        return query.first()

    def get_by_transaction_id(self, transaction_id: str, tenant_id: Optional[int] = None) -> Optional[Payment]:
        """Получить платёж по transaction_id."""
        query = self._db.query(Payment).filter(Payment.transaction_id == transaction_id)
        
        if tenant_id is None:
            current_tenant = get_current_tenant()
            if current_tenant:
                tenant_id = current_tenant.id
        
        if tenant_id is not None:
            query = query.filter(Payment.tenant_id == tenant_id)
            
        return query.first()

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
        if order_id:
            payment = (
                self._db.query(Payment)
                .filter(Payment.order_id == order_id)
                .with_for_update()
                .first()
            )
        elif payment_id:
            payment = (
                self._db.query(Payment)
                .filter(Payment.payment_id == payment_id)
                .with_for_update()
                .first()
            )
        elif transaction_id:
            payment = (
                self._db.query(Payment)
                .filter(Payment.transaction_id == transaction_id)
                .with_for_update()
                .first()
            )
        else:
            return None

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
            
            # Отправляем WebSocket уведомление
            try:
                from app.websocket.notifications import send_payment_notification
                send_payment_notification(
                    order_id=payment.order_id,
                    payment_id=payment.payment_id,
                    status=status_value,
                    amount=payment.amount,
                    currency=payment.currency,
                    gateway=payment.payment_gateway,
                    payment_data=metadata,
                )
            except Exception as ws_error:
                logger.warning(f"Failed to send WebSocket notification: {ws_error}")
                
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

    def get_all_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[Union[str, PaymentStatus]] = None,
        gateway: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        tenant_id: Optional[int] = None,
    ) -> Tuple[List[Payment], int]:
        """
        Получить все платежи с пагинацией, фильтрами и сортировкой.

        Args:
            page: Номер страницы (1-based)
            page_size: Размер страницы (1-100)
            status: Фильтр по статусу
            gateway: Фильтр по платёжной системе
            search: Поиск по order_id или payment_id
            sort_by: Поле для сортировки (created_at, amount, status, gateway)
            sort_order: Порядок сортировки (asc, desc)
            date_from: Дата начала периода
            date_to: Дата конца периода
            tenant_id: Фильтр по tenant (опционально)

        Returns:
            Tuple[List[Payment], int]: Список платежей и общее количество
        """
        query = self._db.query(Payment)

        # Если tenant_id не указан, используем текущий из контекста
        if tenant_id is None:
            current_tenant = get_current_tenant()
            if current_tenant:
                tenant_id = current_tenant.id
        
        # Фильтруем по tenant если он указан
        if tenant_id is not None:
            query = query.filter(Payment.tenant_id == tenant_id)

        # Применяем фильтры
        if status:
            status_value = status.value if isinstance(status, PaymentStatus) else status
            query = query.filter(Payment.status == status_value)

        if gateway:
            query = query.filter(Payment.payment_gateway == gateway)

        if search:
            # Escape special LIKE characters to prevent SQL injection
            escaped_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.filter(
                or_(
                    Payment.order_id.ilike(f"%{escaped_search}%", escape="\\"),
                    Payment.payment_id.ilike(f"%{escaped_search}%", escape="\\"),
                )
            )

        if date_from:
            query = query.filter(Payment.created_at >= date_from)

        if date_to:
            query = query.filter(Payment.created_at <= date_to)

        # Общее количество
        total = query.count()

        # Сортировка с whitelist
        ALLOWED_SORT = {"created_at", "amount", "status", "payment_gateway", "order_id"}
        if sort_by in ALLOWED_SORT:
            sort_column = getattr(Payment, sort_by)
        else:
            sort_column = Payment.created_at
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Пагинация
        offset = (page - 1) * page_size
        payments = query.offset(offset).limit(page_size).all()

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

    def get_statistics(self, tenant_id: Optional[int] = None) -> Dict[str, Any]:
        """Получить статистику."""
        query = self._db.query(Payment)
        
        # Если tenant_id не указан, используем текущий из контекста
        if tenant_id is None:
            current_tenant = get_current_tenant()
            if current_tenant:
                tenant_id = current_tenant.id
        
        # Фильтруем по tenant если он указан
        if tenant_id is not None:
            query = query.filter(Payment.tenant_id == tenant_id)
        
        total = query.count()
        by_status = (
            query.with_entities(Payment.status, func.count(Payment.id))
            .group_by(Payment.status)
            .all()
        )
        by_gateway = (
            query.with_entities(Payment.payment_gateway, func.count(Payment.id))
            .group_by(Payment.payment_gateway)
            .all()
        )
        total_amount = (
            query.with_entities(func.sum(Payment.amount))
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

    def get_analytics(
        self,
        start_date: datetime,
        end_date: datetime,
        tenant_id: Optional[int] = None,
        gateway: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Получить аналитику платежей за период.

        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            tenant_id: Фильтр по tenant
            gateway: Фильтр по платёжной системе

        Returns:
            Статистика за период
        """
        query = self._db.query(Payment).filter(
            Payment.created_at >= start_date,
            Payment.created_at <= end_date,
        )

        if tenant_id is not None:
            query = query.filter(Payment.tenant_id == tenant_id)

        if gateway:
            query = query.filter(Payment.payment_gateway == gateway)

        # Общая статистика
        total = query.count()
        total_amount = (
            query.with_entities(func.sum(Payment.amount))
            .filter(Payment.status == PaymentStatus.COMPLETED)
            .scalar() or 0
        )

        # По статусам
        by_status = dict(
            query.with_entities(Payment.status, func.count(Payment.id))
            .group_by(Payment.status)
            .all()
        )

        # По шлюзам
        by_gateway = dict(
            query.with_entities(Payment.payment_gateway, func.count(Payment.id))
            .group_by(Payment.payment_gateway)
            .all()
        )

        # По валютам
        by_currency = dict(
            query.with_entities(Payment.currency, func.sum(Payment.amount))
            .group_by(Payment.currency)
            .all()
        )

        # Динамика по дням
        daily_stats = (
            query.with_entities(
                func.date(Payment.created_at).label('date'),
                Payment.status,
                func.count(Payment.id).label('count'),
                func.sum(Payment.amount).label('amount')
            )
            .filter(Payment.status == PaymentStatus.COMPLETED)
            .group_by(func.date(Payment.created_at), Payment.status)
            .all()
        )

        daily = {}
        for stat in daily_stats:
            date_str = str(stat.date)
            if date_str not in daily:
                daily[date_str] = {'count': 0, 'amount': 0}
            daily[date_str]['count'] += stat.count
            daily[date_str]['amount'] = float(stat.amount or 0)

        # Средний чек
        avg_check = (
            query.with_entities(func.avg(Payment.amount))
            .filter(Payment.status == PaymentStatus.COMPLETED)
            .scalar() or 0
        )

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "summary": {
                "total_transactions": total,
                "total_amount": float(total_amount),
                "average_check": round(float(avg_check), 2),
            },
            "by_status": {s.value: c for s, c in by_status.items()},
            "by_gateway": by_gateway,
            "by_currency": {c: float(a or 0) for c, a in by_currency.items()},
            "daily_stats": daily,
        }

    def get_dashboard_stats(self, limit: int = 10, tenant_id: Optional[int] = None) -> Dict[str, Any]:
        """Получить расширенную статистику для дашборда."""
        from datetime import timedelta

        query = self._db.query(Payment)
        
        # Если tenant_id не указан, используем текущий из контекста
        if tenant_id is None:
            current_tenant = get_current_tenant()
            if current_tenant:
                tenant_id = current_tenant.id
        
        # Фильтруем по tenant если он указан
        if tenant_id is not None:
            query = query.filter(Payment.tenant_id == tenant_id)

        total = query.count()
        total_amount = (
            query.with_entities(func.sum(Payment.amount))
            .filter(Payment.status == PaymentStatus.COMPLETED)
            .scalar()
            or 0
        )
        by_status = dict(
            query.with_entities(Payment.status, func.count(Payment.id))
            .group_by(Payment.status)
            .all()
        )
        by_gateway = dict(
            query.with_entities(Payment.payment_gateway, func.count(Payment.id))
            .group_by(Payment.payment_gateway)
            .all()
        )

        recent_payments = (
            query.order_by(Payment.created_at.desc())
            .limit(limit)
            .all()
        )

        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        daily_stats = (
            query.with_entities(
                func.date(Payment.created_at).label('date'),
                func.sum(Payment.amount).label('amount')
            )
            .filter(
                Payment.created_at >= seven_days_ago,
                Payment.status == PaymentStatus.COMPLETED
            )
            .group_by(func.date(Payment.created_at))
            .all()
        )
        daily_amount = {str(stat.date): float(stat.amount) for stat in daily_stats}

        return {
            "total_payments": total,
            "total_amount": float(total_amount),
            "by_status": by_status,
            "by_gateway": by_gateway,
            "recent_payments": recent_payments,
            "daily_amount": daily_amount,
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

    def get_payments_by_period(
        self,
        start_date: datetime,
        end_date: datetime,
        gateway: Optional[str] = None,
        status: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> List[Payment]:
        """
        Получить платежи за период с фильтрами.
        
        Args:
            start_date: Начальная дата
            end_date: Конечная дата
            gateway: Фильтр по платёжной системе
            status: Фильтр по статусу
            tenant_id: Фильтр по tenant ID
            
        Returns:
            Список платежей
        """
        query = self._db.query(Payment).filter(
            Payment.created_at >= start_date,
            Payment.created_at <= end_date,
        )
        
        if gateway:
            query = query.filter(Payment.payment_gateway == gateway)
        
        if status:
            try:
                status_enum = PaymentStatus(status) if not isinstance(status, PaymentStatus) else status
                query = query.filter(Payment.status == status_enum)
            except ValueError:
                logger.warning(f"Invalid payment status filter: {status}")
                return []
        
        if tenant_id:
            query = query.filter(Payment.tenant_id == tenant_id)
        
        return query.order_by(Payment.created_at.desc()).all()
