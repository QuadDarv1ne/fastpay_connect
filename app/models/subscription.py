"""Subscription model for recurring payments."""

from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (Boolean, Column, DateTime, Index, Integer, Numeric,
                        String, Text)

from app.database import Base


class SubscriptionInterval(PyEnum):
    """Billing intervals for subscriptions."""
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class SubscriptionStatus(PyEnum):
    """Subscription lifecycle statuses."""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PAST_DUE = "past_due"


class Subscription(Base):
    """Model for recurring payment subscriptions."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_sub_user_id", "user_id"),
        Index("ix_sub_status", "status"),
        Index("ix_sub_interval", "interval"),
        Index("ix_sub_next_billing", "next_billing_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    plan_id = Column(String, nullable=False, index=True)
    plan_name = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="RUB")
    interval = Column(String, nullable=False)  # weekly, monthly, quarterly, yearly
    status = Column(String, default=SubscriptionStatus.ACTIVE.value, index=True)
    payment_gateway = Column(String, nullable=False)
    gateway_subscription_id = Column(String, nullable=True)
    trial_end = Column(DateTime, nullable=True)
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)
    next_billing_date = Column(DateTime, nullable=False, index=True)
    cancel_at_period_end = Column(Boolean, default=False)
    cancellation_reason = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, plan={self.plan_name}, status={self.status})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "plan_id": self.plan_id,
            "plan_name": self.plan_name,
            "amount": float(self.amount),
            "currency": self.currency,
            "interval": self.interval,
            "status": self.status,
            "payment_gateway": self.payment_gateway,
            "trial_end": self.trial_end.isoformat() if self.trial_end else None,
            "current_period_start": self.current_period_start.isoformat() if self.current_period_start else None,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "next_billing_date": self.next_billing_date.isoformat() if self.next_billing_date else None,
            "cancel_at_period_end": self.cancel_at_period_end,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
