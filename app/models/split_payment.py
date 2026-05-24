"""Split payment model for marketplace support.

Allows a single payment to be distributed among multiple recipients.
Each recipient gets a defined share of the total amount.
"""

import enum
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (Column, DateTime, Enum, ForeignKey, Index, Integer,
                        Numeric, String)
from sqlalchemy.orm import relationship

from app.database import Base


class SplitStatus(enum.Enum):
    """Status of a split payment recipient."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class SplitPayment(Base):
    """Represents a split payment distribution.

    A split payment defines how a parent payment is distributed
    among multiple recipients (vendors, platform, etc.).
    """
    __tablename__ = "split_payments"
    __table_args__ = (
        Index("ix_split_parent_payment", "parent_payment_id"),
        Index("ix_split_recipient", "recipient_id"),
        Index("ix_split_status", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    parent_payment_id = Column(Integer, ForeignKey("payments.id"), nullable=False, index=True)
    order_id = Column(String, nullable=False, index=True)

    # Recipient info
    recipient_id = Column(String, nullable=False, index=True)  # Vendor/marketplace ID
    recipient_name = Column(String)
    recipient_type = Column(String, default="vendor")  # vendor, platform, affiliate, tax

    # Amount info
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="RUB")
    commission_percent = Column(Numeric(5, 2), default=0)  # Platform commission %
    commission_amount = Column(Numeric(10, 2), default=0)

    # Status
    status = Column(Enum(SplitStatus, values_callable=lambda x: [e.value for e in x]), default=SplitStatus.PENDING, index=True)

    # Gateway-specific data
    gateway_payment_id = Column(String)
    gateway = Column(String)

    # Metadata
    metadata_json = Column(String)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    parent_payment = relationship("Payment", backref="splits")

    def __repr__(self) -> str:
        return f"<SplitPayment(recipient={self.recipient_id}, amount={self.amount}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert split payment to dictionary."""
        return {
            "id": self.id,
            "parent_payment_id": self.parent_payment_id,
            "order_id": self.order_id,
            "recipient_id": self.recipient_id,
            "recipient_name": self.recipient_name,
            "recipient_type": self.recipient_type,
            "amount": float(self.amount),
            "currency": self.currency,
            "commission_percent": float(self.commission_percent) if self.commission_percent else 0,
            "commission_amount": float(self.commission_amount) if self.commission_amount else 0,
            "status": self.status.value if isinstance(self.status, SplitStatus) else str(self.status),
            "gateway_payment_id": self.gateway_payment_id,
            "gateway": self.gateway,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
