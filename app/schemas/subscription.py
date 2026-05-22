"""Pydantic schemas for subscriptions."""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SubscriptionIntervalEnum(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class SubscriptionStatusEnum(str, Enum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"


class SubscriptionCreateRequest(BaseModel):
    """Create subscription request."""

    plan_id: str = Field(..., max_length=100, description="Plan identifier")
    plan_name: str = Field(..., max_length=200, description="Plan display name")
    amount: float = Field(..., gt=0, le=10_000_000, description="Recurring amount")
    currency: str = Field(default="RUB", max_length=3)
    interval: SubscriptionIntervalEnum = Field(default=SubscriptionIntervalEnum.MONTHLY)
    payment_gateway: str = Field(..., description="Payment gateway for recurring charges")
    trial_days: Optional[int] = Field(None, ge=1, le=365, description="Trial period in days")
    metadata: Optional[Dict[str, str]] = Field(None, description="Custom metadata")

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        return round(v, 2)


class SubscriptionResponse(BaseModel):
    """Subscription response."""

    id: int
    user_id: int
    plan_id: str
    plan_name: str
    amount: float
    currency: str
    interval: str
    status: SubscriptionStatusEnum
    payment_gateway: str
    trial_end: Optional[datetime] = None
    current_period_start: datetime
    current_period_end: datetime
    next_billing_date: datetime
    cancel_at_period_end: bool
    created_at: Optional[datetime] = None


class SubscriptionListResponse(BaseModel):
    """Paginated subscription list."""

    items: list[SubscriptionResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SubscriptionCancelRequest(BaseModel):
    """Cancel subscription request."""

    reason: Optional[str] = Field(None, max_length=500, description="Cancellation reason")
    cancel_at_period_end: bool = Field(
        default=True,
        description="If true, cancel at end of current period; if false, cancel immediately",
    )


class SubscriptionActionResponse(BaseModel):
    """Subscription action result."""

    success: bool
    subscription_id: int
    status: SubscriptionStatusEnum
    message: str
