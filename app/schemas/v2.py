"""Pydantic v2 response models for API v2."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PaymentStatusEnum(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class CurrencyEnum(str, Enum):
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


class PaymentCreateRequest(BaseModel):
    """Create payment request (v2)."""

    order_id: Optional[str] = Field(None, max_length=100, description="Order ID (auto-generated if omitted)")
    gateway: str = Field(default="yookassa", description="Payment gateway")
    amount: float = Field(..., gt=0, le=10_000_000, description="Amount")
    currency: CurrencyEnum = Field(default=CurrencyEnum.RUB)
    description: str = Field(default="", max_length=500)
    idempotency_key: Optional[str] = Field(None, max_length=64, description="Idempotency key for safe retries")
    metadata: Optional[Dict[str, str]] = Field(None, description="Custom metadata")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        return round(v, 2)


class PaymentResponse(BaseModel):
    """Create payment response (v2)."""

    success: bool
    payment_id: Optional[str] = None
    order_id: str
    amount: float
    currency: str
    status: PaymentStatusEnum
    payment_url: Optional[str] = None
    message: str


class PaymentStatusResponse(BaseModel):
    """Payment status response (v2)."""

    order_id: str
    payment_id: Optional[str]
    status: PaymentStatusEnum
    amount: float
    currency: str
    payment_gateway: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    metadata: Optional[Dict[str, Any]] = None


class IdempotencyResponse(BaseModel):
    """Idempotency check response."""

    is_duplicate: bool
    original_payment_id: Optional[str] = None


class WebhookStatusResponse(BaseModel):
    """Webhook processing result (v2)."""

    status: str
    order_id: Optional[str]
    payment_gateway: str
    event_type: Optional[str]
    processed: bool
    message: str


class AdminPaymentInfo(BaseModel):
    """Admin payment info (v2)."""

    order_id: str
    payment_id: Optional[str]
    payment_gateway: str
    amount: float
    currency: str
    status: PaymentStatusEnum
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


class AdminStatisticsResponse(BaseModel):
    """Admin statistics (v2)."""

    total_payments: int
    by_status: Dict[str, int]
    by_gateway: Dict[str, int]
    total_completed_amount: float


class AdminActionResponse(BaseModel):
    """Admin action result (v2)."""

    status: str
    message: str
    order_id: str
    new_status: PaymentStatusEnum


class AuditLogEntry(BaseModel):
    """Audit log entry (v2)."""

    id: int
    user_id: int
    username: str
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[str]
    ip_address: Optional[str]
    created_at: Optional[datetime]


class PaginatedAuditLogs(BaseModel):
    """Paginated audit logs (v2)."""

    items: List[AuditLogEntry]
    total: int
    page: int
    page_size: int
    pages: int
