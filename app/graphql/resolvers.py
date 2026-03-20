"""
GraphQL resolvers для FastPay Connect.
Автор: Dupley Maxim Igorevich
"""

import strawberry
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from datetime import datetime
from enum import Enum
import base64

from app.models.payment import Payment as PaymentModel, PaymentStatus
from app.models.tenant import Tenant as TenantModel
from app.models.webhook_event import WebhookEvent as WebhookEventModel
from app.database import SessionLocal


def get_db() -> Session:
    """Получить сессию БД."""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


def encode_cursor(value: int) -> str:
    """Кодирование курсора для Relay пагинации."""
    return base64.b64encode(f"cursor:{value}".encode()).decode()


def decode_cursor(cursor: str) -> Optional[int]:
    """Декодирование курсора."""
    try:
        decoded = base64.b64decode(cursor.encode()).decode()
        if decoded.startswith("cursor:"):
            return int(decoded[7:])
    except (ValueError, Exception):
        pass
    return None


def payment_model_to_graphql(payment: PaymentModel) -> strawberry.types.types.Payment:
    """Конвертация модели Payment в GraphQL тип."""
    from app.graphql.schema import Payment, PaymentStatusEnum
    
    return Payment(
        id=payment.id,
        order_id=payment.order_id,
        payment_id=payment.payment_id,
        transaction_id=payment.transaction_id,
        payment_gateway=payment.payment_gateway,
        amount=payment.amount,
        currency=payment.currency,
        status=PaymentStatusEnum(payment.status),
        description=payment.description,
        payment_url=payment.payment_url,
        customer_email=payment.customer_email,
        customer_ip=payment.customer_ip,
        tenant_id=payment.tenant_id,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
        refunded_amount=payment.refunded_amount,
        metadata=payment.metadata,
    )


def tenant_model_to_graphql(tenant: TenantModel) -> strawberry.types.types.Tenant:
    """Конвертация модели Tenant в GraphQL тип."""
    from app.graphql.schema import Tenant
    
    return Tenant(
        id=tenant.id,
        name=tenant.name,
        api_key=tenant.api_key,
        is_active=tenant.is_active,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        webhook_url=tenant.webhook_url,
        settings=tenant.settings,
    )


def webhook_model_to_graphql(webhook: WebhookEventModel) -> strawberry.types.types.WebhookEvent:
    """Конвертация модели WebhookEvent в GraphQL тип."""
    from app.graphql.schema import WebhookEvent, WebhookEventType, WebhookEventStatus
    
    return WebhookEvent(
        id=webhook.id,
        event_type=WebhookEventType(webhook.event_type),
        event_status=WebhookEventStatus(webhook.event_status),
        payment_id=webhook.payment_id,
        tenant_id=webhook.tenant_id,
        payload=webhook.payload,
        response=webhook.response,
        response_status=webhook.response_status,
        retry_count=webhook.retry_count,
        max_retries=webhook.max_retries,
        processed=webhook.processed,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
        next_retry_at=webhook.next_retry_at,
    )


@strawberry.type
class PaymentQuery:
    """Query resolver для платежей."""

    @strawberry.field
    def payment(self, order_id: str) -> Optional[strawberry.types.types.Payment]:
        """Получить платёж по order_id."""
        db = get_db()
        payment = db.query(PaymentModel).filter(PaymentModel.order_id == order_id).first()
        db.close()

        if not payment:
            return None

        return payment_model_to_graphql(payment)

    @strawberry.field
    def payment_by_id(self, payment_id: int) -> Optional[strawberry.types.types.Payment]:
        """Получить платёж по ID."""
        db = get_db()
        payment = db.query(PaymentModel).filter(PaymentModel.id == payment_id).first()
        db.close()

        if not payment:
            return None

        return payment_model_to_graphql(payment)

    @strawberry.field
    def payments(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        gateway: Optional[str] = None,
        currency: Optional[str] = None,
        tenant_id: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> strawberry.types.types.PaymentConnection:
        """Получить список платежей с пагинацией и фильтрами."""
        db = get_db()

        query = db.query(PaymentModel)

        # Фильтры
        if status:
            query = query.filter(PaymentModel.status == status)

        if gateway:
            query = query.filter(PaymentModel.payment_gateway == gateway)

        if currency:
            query = query.filter(PaymentModel.currency == currency)

        if tenant_id:
            query = query.filter(PaymentModel.tenant_id == tenant_id)

        if min_amount is not None:
            query = query.filter(PaymentModel.amount >= min_amount)

        if max_amount is not None:
            query = query.filter(PaymentModel.amount <= max_amount)

        if search:
            query = query.filter(
                or_(
                    PaymentModel.order_id.ilike(f"%{search}%"),
                    PaymentModel.payment_id.ilike(f"%{search}%"),
                    PaymentModel.transaction_id.ilike(f"%{search}%"),
                )
            )

        # Общее количество
        total = query.count()

        # Сортировка
        sort_column = getattr(PaymentModel, sort_by, PaymentModel.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Пагинация
        offset = (page - 1) * page_size
        payments = query.offset(offset).limit(page_size).all()
        db.close()

        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        
        # Создаём edges для Relay пагинации
        edges = [
            strawberry.types.types.PaymentEdge(cursor=encode_cursor(p.id), node=payment_model_to_graphql(p))
            for p in payments
        ]

        return strawberry.types.types.PaymentConnection(
            items=[payment_model_to_graphql(p) for p in payments],
            edges=edges,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            has_next=offset + page_size < total,
            has_previous=page > 1,
        )

    @strawberry.field
    def payments_by_cursor(
        self,
        first: Optional[int] = None,
        after: Optional[str] = None,
        last: Optional[int] = None,
        before: Optional[str] = None,
    ) -> strawberry.types.types.PaymentConnection:
        """Получить платежи с cursor-based пагинацией (Relay style)."""
        db = get_db()
        query = db.query(PaymentModel).order_by(PaymentModel.id.asc())

        if after:
            cursor_id = decode_cursor(after)
            if cursor_id:
                query = query.filter(PaymentModel.id > cursor_id)

        if before:
            cursor_id = decode_cursor(before)
            if cursor_id:
                query = query.filter(PaymentModel.id < cursor_id)

        limit = first or last or 20
        payments = query.limit(limit + 1).all()
        db.close()

        has_next = len(payments) > limit
        if has_next:
            payments = payments[:-1]

        edges = [
            strawberry.types.types.PaymentEdge(cursor=encode_cursor(p.id), node=payment_model_to_graphql(p))
            for p in payments
        ]

        # Получаем общий count
        total = db.query(PaymentModel).count()

        return strawberry.types.types.PaymentConnection(
            items=[payment_model_to_graphql(p) for p in payments],
            edges=edges,
            total=total,
            page=1,
            page_size=limit,
            pages=(total + limit - 1) // limit,
            has_next=has_next,
            has_previous=after is not None or before is not None,
        )

    @strawberry.field
    def statistics(
        self,
        gateway: Optional[str] = None,
        tenant_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> strawberry.types.types.PaymentStatistics:
        """Получить расширенную статистику по платежам."""
        db = get_db()

        base_query = db.query(PaymentModel)

        # Применяем фильтры
        if gateway:
            base_query = base_query.filter(PaymentModel.payment_gateway == gateway)

        if tenant_id:
            base_query = base_query.filter(PaymentModel.tenant_id == tenant_id)

        if date_from:
            base_query = base_query.filter(PaymentModel.created_at >= date_from)

        if date_to:
            base_query = base_query.filter(PaymentModel.created_at <= date_to)

        total = base_query.count()

        by_status_query = base_query.with_entities(
            PaymentModel.status, func.count(PaymentModel.id)
        ).group_by(PaymentModel.status).all()

        by_gateway_query = base_query.with_entities(
            PaymentModel.payment_gateway, func.count(PaymentModel.id)
        ).group_by(PaymentModel.payment_gateway).all()

        by_currency_query = base_query.with_entities(
            PaymentModel.currency, func.count(PaymentModel.id)
        ).group_by(PaymentModel.currency).all()

        total_amount_result = base_query.filter(
            PaymentModel.status == PaymentStatus.COMPLETED.value
        ).with_entities(func.sum(PaymentModel.amount)).scalar() or 0.0

        average_payment = base_query.with_entities(func.avg(PaymentModel.amount)).scalar() or 0.0

        # Daily revenue (last 7 days)
        from sqlalchemy import extract
        daily_revenue_query = base_query.filter(
            PaymentModel.status == PaymentStatus.COMPLETED.value,
            PaymentModel.created_at >= func.now() - 7
        ).with_entities(
            extract('day', PaymentModel.created_at).label('day'),
            func.sum(PaymentModel.amount).label('revenue')
        ).group_by(
            extract('day', PaymentModel.created_at)
        ).all()

        db.close()

        return strawberry.types.types.PaymentStatistics(
            total_payments=total,
            total_amount=float(total_amount_result),
            by_status={status: count for status, count in by_status_query},
            by_gateway={gateway: count for gateway, count in by_gateway_query},
            by_currency={currency: count for currency, count in by_currency_query},
            daily_revenue={str(day): float(rev) for day, rev in daily_revenue_query},
            average_payment=float(average_payment),
        )


@strawberry.type
class TenantQuery:
    """Query resolver для тенантов."""

    @strawberry.field
    def tenant(self, tenant_id: int) -> Optional[strawberry.types.types.Tenant]:
        """Получить тенанта по ID."""
        db = get_db()
        tenant = db.query(TenantModel).filter(TenantModel.id == tenant_id).first()
        db.close()

        if not tenant:
            return None

        return tenant_model_to_graphql(tenant)

    @strawberry.field
    def tenant_by_api_key(self, api_key: str) -> Optional[strawberry.types.types.Tenant]:
        """Получить тенанта по API ключу."""
        db = get_db()
        tenant = db.query(TenantModel).filter(TenantModel.api_key == api_key).first()
        db.close()

        if not tenant:
            return None

        return tenant_model_to_graphql(tenant)

    @strawberry.field
    def tenants(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> strawberry.types.types.TenantConnection:
        """Получить список тенантов."""
        db = get_db()

        query = db.query(TenantModel)

        if is_active is not None:
            query = query.filter(TenantModel.is_active == is_active)

        if search:
            query = query.filter(
                or_(
                    TenantModel.name.ilike(f"%{search}%"),
                    TenantModel.api_key.ilike(f"%{search}%"),
                )
            )

        total = query.count()
        offset = (page - 1) * page_size
        tenants = query.offset(offset).limit(page_size).all()
        db.close()

        pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return strawberry.types.types.TenantConnection(
            items=[tenant_model_to_graphql(t) for t in tenants],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )


@strawberry.type
class WebhookQuery:
    """Query resolver для webhook событий."""

    @strawberry.field
    def webhook_event(self, event_id: int) -> Optional[strawberry.types.types.WebhookEvent]:
        """Получить webhook событие по ID."""
        db = get_db()
        event = db.query(WebhookEventModel).filter(WebhookEventModel.id == event_id).first()
        db.close()

        if not event:
            return None

        return webhook_model_to_graphql(event)

    @strawberry.field
    def webhook_events(
        self,
        page: int = 1,
        page_size: int = 20,
        event_type: Optional[str] = None,
        event_status: Optional[str] = None,
        processed: Optional[bool] = None,
        tenant_id: Optional[int] = None,
    ) -> strawberry.types.types.WebhookEventConnection:
        """Получить список webhook событий."""
        db = get_db()

        query = db.query(WebhookEventModel)

        if event_type:
            query = query.filter(WebhookEventModel.event_type == event_type)

        if event_status:
            query = query.filter(WebhookEventModel.event_status == event_status)

        if processed is not None:
            query = query.filter(WebhookEventModel.processed == processed)

        if tenant_id:
            query = query.filter(WebhookEventModel.tenant_id == tenant_id)

        total = query.count()
        offset = (page - 1) * page_size
        events = query.offset(offset).limit(page_size).all()
        db.close()

        pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return strawberry.types.types.WebhookEventConnection(
            items=[webhook_model_to_graphql(e) for e in events],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )


@strawberry.type
class PaymentMutation:
    """Mutation resolver для платежей."""

    @strawberry.field
    def ping(self) -> str:
        """Test mutation."""
        return "pong"


# Объединяем все query и mutation
@strawberry.type
class GraphQLQuery(PaymentQuery, TenantQuery, WebhookQuery):
    """Объединённый Query."""
    pass


@strawberry.type
class GraphQLMutation(PaymentMutation):
    """Объединённый Mutation."""
    pass


schema = strawberry.Schema(query=GraphQLQuery, mutation=GraphQLMutation)
