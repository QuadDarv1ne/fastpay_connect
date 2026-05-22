"""
GraphQL resolvers для FastPay Connect.
Автор: Dupley Maxim Igorevich
"""

import strawberry
from typing import List, Optional
from strawberry.types import Info
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_
from datetime import datetime, timezone
from enum import Enum
import base64
import logging
from contextlib import contextmanager

from app.graphql.context import get_graphql_context

logger = logging.getLogger(__name__)

from app.models.payment import Payment as PaymentModel, PaymentStatus
from app.models.tenant import Tenant as TenantModel
from app.models.webhook_event import WebhookEvent as WebhookEventModel
from app.database import SessionLocal
from app.graphql.schema import (
    Payment as PaymentType,
    Tenant as TenantType,
    WebhookEvent as WebhookEventType,
    PaymentEdge as PaymentTypeEdge,
    PaymentConnection as PaymentTypeConnection,
    PaymentStatistics as PaymentTypeStatistics,
    TenantConnection as TenantTypeConnection,
    WebhookEventConnection as WebhookEventTypeConnection,
)


@contextmanager
def get_db() -> Session:
    """Контекстный менеджер для сессии БД — гарантирует закрытие даже при исключении."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def encode_cursor(value: int) -> str:
    """Кодирование курсора для Relay пагинации."""
    return base64.b64encode(f"cursor:{value}".encode()).decode()


def decode_cursor(cursor: str) -> Optional[int]:
    """Декодирование курсора."""
    # Limit cursor length to prevent abuse
    if not cursor or len(cursor) > 256:
        logger.debug(f"Cursor rejected: invalid length ({len(cursor) if cursor else 0})")
        return None
    try:
        decoded = base64.b64decode(cursor.encode()).decode()
        if decoded.startswith("cursor:"):
            return int(decoded[7:])
    except (ValueError, Exception) as e:
        logger.debug(f"Failed to decode cursor '{cursor}': {e}")
    return None


def payment_model_to_graphql(payment: PaymentModel) -> PaymentType:
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
        tenant_id=payment.tenant_id,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
        metadata=payment.metadata_json,
    )


def tenant_model_to_graphql(tenant: TenantModel) -> TenantType:
    """Конвертация модели Tenant в GraphQL тип."""
    from app.graphql.schema import Tenant

    # Mask API key for security: show only first 4 and last 4 chars
    api_key = tenant.api_key or ""
    if len(api_key) > 8:
        masked_key = api_key[:4] + "..." + api_key[-4:]
    elif api_key:
        masked_key = "****"
    else:
        masked_key = ""

    return Tenant(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        masked_api_key=masked_key,
        status=tenant.status,
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        settings_json=tenant.settings_json,
        description=tenant.description,
        contact_email=tenant.contact_email,
    )


def webhook_model_to_graphql(webhook: WebhookEventModel) -> WebhookEventType:
    """Конвертация модели WebhookEvent в GraphQL тип."""
    from app.graphql.schema import WebhookEvent, WebhookEventType, WebhookEventStatus

    # Map model fields to GraphQL type fields based on actual model schema
    return WebhookEvent(
        id=webhook.id,
        event_type=WebhookEventType(webhook.gateway) if hasattr(WebhookEventType, webhook.gateway) else WebhookEventType.UNKNOWN,
        event_status=WebhookEventStatus(webhook.status.value if hasattr(webhook.status, 'value') else webhook.status),
        payment_id=webhook.order_id,  # order_id serves as payment reference
        tenant_id=None,  # WebhookEvent model does not have tenant_id
        payload=webhook.payload or {},
        response=webhook.last_error,  # last_error serves as response info
        response_status=webhook.status.value if hasattr(webhook.status, 'value') else webhook.status,
        retry_count=webhook.retry_count,
        max_retries=webhook.max_retries,
        processed=webhook.processed_at is not None,
        created_at=webhook.created_at,
        updated_at=webhook.updated_at,
        next_retry_at=webhook.next_retry_at,
    )


# Maximum page size to prevent DoS
MAX_PAGE_SIZE = 100


def _get_ctx(info: Info) -> dict:
    """Extract context from Strawberry info."""
    ctx = info.context
    # Strawberry wraps dict context in an object, access directly
    if isinstance(ctx, dict):
        return ctx
    # If it's a custom object, try to get attributes
    return getattr(ctx, "__dict__", {}) or {}


@strawberry.type
class PaymentQuery:
    """Query resolver для платежей."""

    @strawberry.field
    def payment(self, info: Info, order_id: str) -> Optional[PaymentType]:
        """Получить платёж по order_id."""
        ctx = _get_ctx(info)
        if not ctx.get("user_id"):
            return None

        with get_db() as db:
            query = db.query(PaymentModel).filter(PaymentModel.order_id == order_id)
            # Non-admin users can only see their own tenant's payments
            if not ctx.get("is_admin"):
                query = query.filter(PaymentModel.tenant_id == ctx["user_id"])
            payment = query.first()

        if not payment:
            return None

        return payment_model_to_graphql(payment)

    @strawberry.field
    def payment_by_id(self, info: Info, payment_id: int) -> Optional[PaymentType]:
        """Получить платёж по ID."""
        ctx = _get_ctx(info)
        if not ctx.get("user_id"):
            return None

        with get_db() as db:
            query = db.query(PaymentModel).filter(PaymentModel.id == payment_id)
            if not ctx.get("is_admin"):
                query = query.filter(PaymentModel.tenant_id == ctx["user_id"])
            payment = query.first()

        if not payment:
            return None

        return payment_model_to_graphql(payment)

    @strawberry.field
    def payments(
        self,
        info: Info,
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
    ) -> PaymentTypeConnection:
        """Получить список платежей с пагинацией и фильтрами."""
        ctx = _get_ctx(info)
        if not ctx.get("user_id"):
            return PaymentTypeConnection(items=[], edges=[], total=0, page=page, page_size=0, pages=0, has_next=False, has_previous=False)

        # Enforce page size limit
        page_size = min(page_size, MAX_PAGE_SIZE)

        with get_db() as db:
            query = db.query(PaymentModel)

            # Non-admin users can only see their own tenant's payments
            if not ctx.get("is_admin"):
                query = query.filter(PaymentModel.tenant_id == ctx.get("user_id"))
            # Admin can filter by tenant_id if provided
            elif tenant_id:
                query = query.filter(PaymentModel.tenant_id == tenant_id)

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
                # Escape special LIKE characters to prevent SQL injection
                escaped_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                query = query.filter(
                    or_(
                        PaymentModel.order_id.ilike(f"%{escaped_search}%", escape="\\"),
                        PaymentModel.payment_id.ilike(f"%{escaped_search}%", escape="\\"),
                        PaymentModel.transaction_id.ilike(f"%{escaped_search}%", escape="\\"),
                    )
                )

            # Общее количество
            total = query.count()

            # Сортировка с whitelist
            ALLOWED_SORT = {"created_at", "amount", "status", "payment_gateway", "order_id", "id"}
            if sort_by in ALLOWED_SORT:
                sort_column = getattr(PaymentModel, sort_by)
            else:
                sort_column = PaymentModel.created_at
            if sort_order.lower() == "asc":
                query = query.order_by(sort_column.asc())
            else:
                query = query.order_by(sort_column.desc())

            # Пагинация
            offset = (page - 1) * page_size
            payments = query.offset(offset).limit(page_size).all()

            pages = (total + page_size - 1) // page_size if page_size > 0 else 0
            
            # Создаём edges для Relay пагинации
            edges = [
                PaymentTypeEdge(cursor=encode_cursor(p.id), node=payment_model_to_graphql(p))
                for p in payments
            ]

            return PaymentTypeConnection(
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
        info: Info,
        first: Optional[int] = None,
        after: Optional[str] = None,
        last: Optional[int] = None,
        before: Optional[str] = None,
    ) -> PaymentTypeConnection:
        """Получить платежи с cursor-based пагинацией (Relay style)."""
        ctx = _get_ctx(info)
        if not ctx.get("user_id"):
            return PaymentTypeConnection(items=[], edges=[], total=0, page=1, page_size=0, pages=0, has_next=False, has_previous=False)

        limit = min(first or last or 20, MAX_PAGE_SIZE)

        with get_db() as db:
            query = db.query(PaymentModel).order_by(PaymentModel.id.asc())
            if not ctx.get("is_admin"):
                query = query.filter(PaymentModel.tenant_id == ctx.get("user_id"))

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

            has_next = len(payments) > limit
            if has_next:
                payments = payments[:-1]

            edges = [
                PaymentTypeEdge(cursor=encode_cursor(p.id), node=payment_model_to_graphql(p))
                for p in payments
            ]

            # Получаем общий count
            total = db.query(PaymentModel).count()

            return PaymentTypeConnection(
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
        info: Info,
        gateway: Optional[str] = None,
        tenant_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> PaymentTypeStatistics:
        """Получить расширенную статистику по платежам."""
        ctx = _get_ctx(info)
        if not ctx.get("user_id"):
            return PaymentTypeStatistics(
                total_payments=0, total_amount=0, by_status={}, by_gateway={},
                by_currency={}, daily_revenue={}, average_payment=0,
            )

        with get_db() as db:
            base_query = db.query(PaymentModel)

            # Non-admin users can only see their own tenant's stats
            if not ctx.get("is_admin"):
                base_query = base_query.filter(PaymentModel.tenant_id == ctx.get("user_id"))
            elif tenant_id:
                base_query = base_query.filter(PaymentModel.tenant_id == tenant_id)

            # Apply additional filters
            if gateway:
                base_query = base_query.filter(PaymentModel.payment_gateway == gateway)

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
            daily_revenue_query = base_query.filter(
                PaymentModel.status == PaymentStatus.COMPLETED.value,
                PaymentModel.created_at >= func.now() - 7
            ).with_entities(
                func.date(PaymentModel.created_at).label('day'),
                func.sum(PaymentModel.amount).label('revenue')
            ).group_by(
                func.date(PaymentModel.created_at)
            ).all()

            return PaymentTypeStatistics(
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
    def tenant(self, info: Info, tenant_id: int) -> Optional[TenantType]:
        """Получить тенанта по ID. Admin only."""
        ctx = _get_ctx(info)
        if not ctx.get("is_admin"):
            return None

        with get_db() as db:
            tenant = db.query(TenantModel).filter(TenantModel.id == tenant_id).first()

        if not tenant:
            return None

        return tenant_model_to_graphql(tenant)

    @strawberry.field
    def tenants(
        self,
        info: Info,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> TenantTypeConnection:
        """Получить список тенантов. Admin only."""
        ctx = _get_ctx(info)
        if not ctx.get("is_admin"):
            return TenantTypeConnection(items=[], total=0, page=page, page_size=0, pages=0)

        page_size = min(page_size, MAX_PAGE_SIZE)

        with get_db() as db:
            query = db.query(TenantModel)

            if is_active is not None:
                if is_active:
                    query = query.filter(TenantModel.status == "active")
                else:
                    query = query.filter(TenantModel.status != "active")

            if search:
                # Escape special LIKE characters to prevent SQL injection
                escaped_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                query = query.filter(
                    or_(
                        TenantModel.name.ilike(f"%{escaped_search}%", escape="\\"),
                        TenantModel.slug.ilike(f"%{escaped_search}%", escape="\\"),
                    )
                )

            total = query.count()
            offset = (page - 1) * page_size
            tenants = query.offset(offset).limit(page_size).all()

            pages = (total + page_size - 1) // page_size if page_size > 0 else 0

            return TenantTypeConnection(
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
    def webhook_event(self, info: Info, event_id: int) -> Optional[WebhookEventType]:
        """Получить webhook событие по ID."""
        ctx = _get_ctx(info)
        if not ctx.get("user_id"):
            return None

        with get_db() as db:
            query = db.query(WebhookEventModel).filter(WebhookEventModel.id == event_id)
            if not ctx.get("is_admin"):
                # Non-admin users can only see their own tenant's webhooks
                tenant_payments = db.query(PaymentModel).filter(PaymentModel.tenant_id == ctx.get("user_id")).all()
                order_ids = [p.order_id for p in tenant_payments]
                if order_ids:
                    query = query.filter(WebhookEventModel.order_id.in_(order_ids))
                else:
                    return None
            event = query.first()

        if not event:
            return None

        return webhook_model_to_graphql(event)

    @strawberry.field
    def webhook_events(
        self,
        info: Info,
        page: int = 1,
        page_size: int = 20,
        event_type: Optional[str] = None,
        event_status: Optional[str] = None,
        processed: Optional[bool] = None,
        tenant_id: Optional[int] = None,
    ) -> WebhookEventTypeConnection:
        """Получить список webhook событий."""
        ctx = _get_ctx(info)
        if not ctx.get("user_id"):
            return WebhookEventTypeConnection(items=[], total=0, page=page, page_size=0, pages=0)

        page_size = min(page_size, MAX_PAGE_SIZE)

        with get_db() as db:
            query = db.query(WebhookEventModel)

            if not ctx.get("is_admin"):
                # Non-admin users can only see their own tenant's webhooks
                # Filter by order_id matching tenant's payments
                tenant_payments = db.query(PaymentModel).filter(PaymentModel.tenant_id == ctx.get("user_id")).all()
                order_ids = [p.order_id for p in tenant_payments]
                if order_ids:
                    query = query.filter(WebhookEventModel.order_id.in_(order_ids))
                else:
                    # No payments for this tenant, return empty
                    return WebhookEventTypeConnection(items=[], total=0, page=page, page_size=0, pages=0)
            elif tenant_id:
                # Admin filtering by tenant - same approach
                tenant_payments = db.query(PaymentModel).filter(PaymentModel.tenant_id == tenant_id).all()
                order_ids = [p.order_id for p in tenant_payments]
                if order_ids:
                    query = query.filter(WebhookEventModel.order_id.in_(order_ids))
                else:
                    return WebhookEventTypeConnection(items=[], total=0, page=page, page_size=0, pages=0)

            if event_type:
                query = query.filter(WebhookEventModel.gateway == event_type)

            if event_status:
                query = query.filter(WebhookEventModel.status == event_status)

            if processed is not None:
                if processed:
                    query = query.filter(WebhookEventModel.processed_at.isnot(None))
                else:
                    query = query.filter(WebhookEventModel.processed_at.is_(None))

            total = query.count()
            offset = (page - 1) * page_size
            events = query.offset(offset).limit(page_size).all()

            pages = (total + page_size - 1) // page_size if page_size > 0 else 0

            return WebhookEventTypeConnection(
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
