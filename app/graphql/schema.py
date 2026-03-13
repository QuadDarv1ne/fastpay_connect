"""
GraphQL схемы для FastPay Connect.
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
    created_at: datetime
    updated_at: datetime


@strawberry.type
class PaymentConnection:
    """Пагинированный список платежей."""
    items: List[Payment]
    total: int
    page: int
    page_size: int
    pages: int


@strawberry.type
class PaymentStatistics:
    """Статистика по платежам."""
    total_payments: int
    total_amount: float
    by_status: Dict[str, int]
    by_gateway: Dict[str, int]
