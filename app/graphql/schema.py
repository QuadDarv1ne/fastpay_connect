"""
GraphQL схемы для FastPay Connect.
Автор: Dupley Maxim Igorevich
"""

import strawberry
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


@strawberry.enum
class PaymentStatusEnum(Enum):
    """Статусы платежа."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@strawberry.enum
class CurrencyEnum(Enum):
    """Валюты."""
    RUB = "RUB"
    USD = "USD"
    EUR = "EUR"
    KZT = "KZT"
    BYN = "BYN"
    CNY = "CNY"
    TRY = "TRY"
    AED = "AED"
    GBP = "GBP"
    JPY = "JPY"


@strawberry.type
class Payment:
    """Тип платежа GraphQL."""
    id: int
    order_id: str
    payment_id: Optional[str]
    transaction_id: Optional[str]
    payment_gateway: str
    amount: float
    currency: str
    status: PaymentStatusEnum
    description: Optional[str]
    payment_url: Optional[str]
    customer_email: Optional[str]
    customer_ip: Optional[str]
    tenant_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    refunded_amount: Optional[float]
    metadata: Optional[str]


@strawberry.type
class PaymentEdge:
    """Ребро для Relay-style пагинации."""
    cursor: str
    node: Payment


@strawberry.type
class PaymentConnection:
    """Пагинированный список платежей."""
    items: List[Payment]
    edges: List[PaymentEdge]
    total: int
    page: int
    page_size: int
    pages: int
    has_next: bool
    has_previous: bool


@strawberry.type
class PaymentStatistics:
    """Статистика по платежам."""
    total_payments: int
    total_amount: float
    by_status: strawberry.scalars.JSON
    by_gateway: strawberry.scalars.JSON
    by_currency: strawberry.scalars.JSON
    daily_revenue: strawberry.scalars.JSON
    average_payment: float


@strawberry.type
class Tenant:
    """Тип тенанта GraphQL."""
    id: int
    name: str
    api_key: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    webhook_url: Optional[str]
    settings: Optional[str]


@strawberry.type
class TenantConnection:
    """Пагинированный список тенантов."""
    items: List[Tenant]
    total: int
    page: int
    page_size: int
    pages: int


@strawberry.enum
class WebhookEventType(Enum):
    """Типы webhook событий."""
    PAYMENT_CREATED = "payment.created"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    PAYMENT_REFUNDED = "payment.refunded"
    PAYMENT_CANCELLED = "payment.cancelled"


@strawberry.enum
class WebhookEventStatus(Enum):
    """Статусы webhook событий."""
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"


@strawberry.type
class WebhookEvent:
    """Тип webhook события GraphQL."""
    id: int
    event_type: WebhookEventType
    event_status: WebhookEventStatus
    payment_id: Optional[int]
    tenant_id: Optional[int]
    payload: strawberry.scalars.JSON
    response: Optional[str]
    response_status: Optional[int]
    retry_count: int
    max_retries: int
    processed: bool
    created_at: datetime
    updated_at: datetime
    next_retry_at: Optional[datetime]


@strawberry.type
class WebhookEventConnection:
    """Пагинированный список webhook событий."""
    items: List[WebhookEvent]
    total: int
    page: int
    page_size: int
    pages: int


@strawberry.input
class PaymentFilterInput:
    """Фильтры для платежей."""
    status: Optional[PaymentStatusEnum] = None
    gateway: Optional[str] = None
    currency: Optional[CurrencyEnum] = None
    tenant_id: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    search: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None


@strawberry.input
class PaginationInput:
    """Параметры пагинации."""
    page: int = 1
    page_size: int = 20
    sort_by: str = "created_at"
    sort_order: str = "desc"
