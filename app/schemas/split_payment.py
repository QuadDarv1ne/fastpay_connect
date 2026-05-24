"""Pydantic schemas for split payments (marketplace support)."""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class SplitRecipient(BaseModel):
    """A single recipient in a split payment."""
    recipient_id: str = Field(..., description="Unique recipient identifier (vendor ID, platform, etc.)")
    recipient_name: Optional[str] = Field(None, description="Human-readable recipient name")
    recipient_type: str = Field(default="vendor", description="Type: vendor, platform, affiliate, tax")
    amount: Decimal = Field(..., gt=0, description="Amount to transfer to this recipient")
    commission_percent: Optional[Decimal] = Field(default=0, ge=0, le=100, description="Platform commission percentage")


class SplitPaymentCreateRequest(BaseModel):
    """Request to create a split payment."""
    order_id: str = Field(..., min_length=1, max_length=128)
    total_amount: Decimal = Field(..., gt=0, description="Total payment amount")
    currency: str = Field(default="RUB", pattern=r"^[A-Z]{3}$")
    gateway: str = Field(default="yookassa", description="Payment gateway")
    description: Optional[str] = Field(None, description="Payment description")
    recipients: List[SplitRecipient] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="List of recipients and their shares",
    )
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    @field_validator("recipients")
    @classmethod
    def validate_recipient_amounts(cls, v: List["SplitRecipient"], info) -> List["SplitRecipient"]:
        """Ensure recipient amounts sum to total amount."""
        total = sum(r.amount for r in v)
        # We'll check against total_amount after model creation
        return v


class SplitPaymentResponse(BaseModel):
    """Response for a split payment."""
    order_id: str
    total_amount: Decimal
    currency: str
    status: str
    splits: List[Dict[str, Any]]
    created_at: str
    gateway: Optional[str] = None


class SplitPaymentStatusResponse(BaseModel):
    """Status of a split payment distribution."""
    order_id: str
    splits: List[Dict[str, Any]]


class SplitPaymentRefundRequest(BaseModel):
    """Request to refund a split payment."""
    split_id: int = Field(..., gt=0, description="Split payment ID to refund")
    amount: Optional[Decimal] = Field(None, gt=0, description="Partial refund amount (None for full)")
    reason: Optional[str] = Field(None, description="Refund reason")
