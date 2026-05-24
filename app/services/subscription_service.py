"""Subscription service for recurring payments."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.subscription import (Subscription, SubscriptionInterval,
                                     SubscriptionStatus)
from app.schemas.subscription import SubscriptionCreateRequest

logger = logging.getLogger(__name__)

# Billing interval → timedelta mapping
INTERVAL_DELTA = {
    SubscriptionInterval.WEEKLY.value: timedelta(weeks=1),
    SubscriptionInterval.MONTHLY.value: timedelta(days=30),
    SubscriptionInterval.QUARTERLY.value: timedelta(days=90),
    SubscriptionInterval.YEARLY.value: timedelta(days=365),
}


class SubscriptionServiceError(Exception):
    """Subscription service error."""
    pass


class SubscriptionService:
    """Service for managing recurring payment subscriptions."""

    def __init__(self, db: Session):
        self.db = db

    def create_subscription(
        self,
        user_id: int,
        request: SubscriptionCreateRequest,
    ) -> Subscription:
        """Create a new subscription."""
        now = datetime.now(timezone.utc)
        interval_delta = INTERVAL_DELTA.get(request.interval.value, timedelta(days=30))

        trial_end = None
        period_start = now
        if request.trial_days:
            trial_end = now + timedelta(days=request.trial_days)
            period_start = trial_end

        period_end = period_start + interval_delta

        sub = Subscription(
            user_id=user_id,
            plan_id=request.plan_id,
            plan_name=request.plan_name,
            amount=request.amount,
            currency=request.currency,
            interval=request.interval.value,
            status=SubscriptionStatus.TRIALING.value if request.trial_days else SubscriptionStatus.ACTIVE.value,
            payment_gateway=request.payment_gateway,
            trial_end=trial_end,
            current_period_start=period_start,
            current_period_end=period_end,
            next_billing_date=period_end,
            metadata_json=json.dumps(request.metadata) if request.metadata else None,
        )

        self.db.add(sub)
        try:
            self.db.commit()
            self.db.refresh(sub)
        except Exception:
            self.db.rollback()
            raise

        logger.info(f"Subscription created: user={user_id}, plan={request.plan_name}, id={sub.id}")
        return sub

    def get_subscription(self, subscription_id: int) -> Optional[Subscription]:
        """Get subscription by ID."""
        return self.db.query(Subscription).filter(Subscription.id == subscription_id).first()

    def get_user_subscriptions(self, user_id: int) -> List[Subscription]:
        """Get all subscriptions for a user."""
        return (
            self.db.query(Subscription)
            .filter(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
            .all()
        )

    def cancel_subscription(
        self,
        subscription_id: int,
        user_id: int,
        reason: Optional[str] = None,
        cancel_at_period_end: bool = True,
    ) -> Optional[Subscription]:
        """Cancel a subscription."""
        sub = (
            self.db.query(Subscription)
            .filter(Subscription.id == subscription_id, Subscription.user_id == user_id)
            .first()
        )

        if not sub:
            return None

        if sub.status == SubscriptionStatus.CANCELLED.value:
            raise SubscriptionServiceError("Subscription already cancelled")

        if cancel_at_period_end:
            sub.cancel_at_period_end = True
            sub.cancellation_reason = reason
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            self.db.refresh(sub)
            logger.info(f"Subscription {sub.id} marked for cancellation at period end")
        else:
            sub.status = SubscriptionStatus.CANCELLED.value
            sub.cancellation_reason = reason
            sub.cancel_at_period_end = False
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise
            self.db.refresh(sub)
            logger.info(f"Subscription {sub.id} cancelled immediately")

        return sub

    def pause_subscription(self, subscription_id: int, user_id: int) -> Optional[Subscription]:
        """Pause a subscription."""
        sub = (
            self.db.query(Subscription)
            .filter(Subscription.id == subscription_id, Subscription.user_id == user_id)
            .first()
        )
        if not sub:
            return None
        if sub.status not in (SubscriptionStatus.ACTIVE.value, SubscriptionStatus.TRIALING.value):
            raise SubscriptionServiceError(f"Cannot pause subscription in status: {sub.status}")

        sub.status = SubscriptionStatus.PAUSED.value
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def resume_subscription(self, subscription_id: int, user_id: int) -> Optional[Subscription]:
        """Resume a paused subscription."""
        sub = (
            self.db.query(Subscription)
            .filter(Subscription.id == subscription_id, Subscription.user_id == user_id)
            .first()
        )
        if not sub:
            return None
        if sub.status != SubscriptionStatus.PAUSED.value:
            raise SubscriptionServiceError(f"Cannot resume subscription in status: {sub.status}")

        sub.status = SubscriptionStatus.ACTIVE.value
        self.db.commit()
        self.db.refresh(sub)
        return sub

    def get_due_subscriptions(self) -> List[Subscription]:
        """Get subscriptions that are due for billing."""
        now = datetime.now(timezone.utc)
        return (
            self.db.query(Subscription)
            .filter(
                Subscription.status == SubscriptionStatus.ACTIVE.value,
                Subscription.next_billing_date <= now,
                Subscription.cancel_at_period_end.is_(False),
            )
            .all()
        )
