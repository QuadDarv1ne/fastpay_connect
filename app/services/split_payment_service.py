"""Split payment service for marketplace support.

Handles creation, distribution, and refund of split payments.
"""

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from app.models.payment import Payment, PaymentStatus
from app.models.split_payment import SplitPayment, SplitStatus
from app.schemas.split_payment import (
    SplitPaymentCreateRequest,
    SplitRecipient,
)

logger = logging.getLogger(__name__)


class SplitPaymentError(Exception):
    """Split payment service error."""

    def __init__(self, message: str, order_id: Optional[str] = None):
        super().__init__(message)
        self.order_id = order_id


class SplitPaymentService:
    """Service for managing split payments."""

    def __init__(self, db: Session):
        self.db = db

    def create_split_payment(self, request: SplitPaymentCreateRequest) -> SplitPayment:
        """Create a split payment with multiple recipients.

        Validates that recipient amounts sum to the total amount.
        Creates the parent payment and all split distributions.
        """
        # Validate recipient amounts
        recipient_total = sum(r.amount for r in request.recipients)
        if abs(recipient_total - request.total_amount) > Decimal("0.01"):
            raise SplitPaymentError(
                f"Recipient amounts ({recipient_total}) do not sum to total ({request.total_amount})",
                order_id=request.order_id,
            )

        # Check for duplicate order
        existing = self.db.query(Payment).filter(Payment.order_id == request.order_id).first()
        if existing:
            raise SplitPaymentError(
                f"Payment with order_id {request.order_id} already exists",
                order_id=request.order_id,
            )

        # Create parent payment
        parent_payment = Payment(
            order_id=request.order_id,
            amount=request.total_amount,
            currency=request.currency,
            payment_gateway=request.gateway,
            description=request.description,
            status=PaymentStatus.PENDING,
            metadata_json=json.dumps(request.metadata) if request.metadata else None,
        )
        self.db.add(parent_payment)
        self.db.flush()

        # Create split distributions
        splits = []
        for recipient in request.recipients:
            commission_amount = Decimal(0)
            if recipient.commission_percent:
                commission_amount = (recipient.amount * recipient.commission_percent / Decimal(100)).quantize(
                    Decimal("0.01")
                )

            split = SplitPayment(
                parent_payment_id=parent_payment.id,
                order_id=request.order_id,
                recipient_id=recipient.recipient_id,
                recipient_name=recipient.recipient_name,
                recipient_type=recipient.recipient_type,
                amount=recipient.amount,
                currency=request.currency,
                commission_percent=recipient.commission_percent or Decimal(0),
                commission_amount=commission_amount,
                status=SplitStatus.PENDING,
                gateway=request.gateway,
            )
            self.db.add(split)
            splits.append(split)

        self.db.commit()
        self.db.refresh(parent_payment)

        logger.info(
            f"Split payment created: order={request.order_id}, "
            f"total={request.total_amount}, recipients={len(splits)}"
        )

        return parent_payment

    def get_split_payments(self, order_id: str) -> List[SplitPayment]:
        """Get all split distributions for a payment."""
        return (
            self.db.query(SplitPayment)
            .filter(SplitPayment.order_id == order_id)
            .all()
        )

    def get_split_payment_by_id(self, split_id: int) -> Optional[SplitPayment]:
        """Get a specific split distribution by ID."""
        return self.db.query(SplitPayment).filter(SplitPayment.id == split_id).first()

    def update_split_status(
        self,
        split_id: int,
        status: SplitStatus,
        gateway_payment_id: Optional[str] = None,
    ) -> SplitPayment:
        """Update the status of a split payment distribution."""
        split = self.get_split_payment_by_id(split_id)
        if not split:
            raise SplitPaymentError(f"Split payment {split_id} not found")

        split.status = status
        if gateway_payment_id:
            split.gateway_payment_id = gateway_payment_id
        if status == SplitStatus.COMPLETED:
            split.completed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(split)

        logger.info(f"Split payment {split_id} status updated to {status.value}")
        return split

    def refund_split_payment(
        self,
        split_id: int,
        amount: Optional[Decimal] = None,
        reason: Optional[str] = None,
    ) -> SplitPayment:
        """Refund a split payment distribution.

        If amount is None, performs a full refund.
        """
        split = self.get_split_payment_by_id(split_id)
        if not split:
            raise SplitPaymentError(f"Split payment {split_id} not found")

        if split.status not in (SplitStatus.COMPLETED, SplitStatus.PROCESSING):
            raise SplitPaymentError(
                f"Cannot refund split payment with status {split.status.value}",
            )

        split.status = SplitStatus.REFUNDED
        metadata = {}
        if split.metadata_json:
            metadata = json.loads(split.metadata_json)
        metadata["refund"] = {
            "amount": str(amount or split.amount),
            "reason": reason,
            "refunded_at": datetime.now(timezone.utc).isoformat(),
        }
        split.metadata_json = json.dumps(metadata)

        self.db.commit()
        self.db.refresh(split)

        logger.info(f"Split payment {split_id} refunded: amount={amount or split.amount}, reason={reason}")
        return split

    def get_pending_splits(self) -> List[SplitPayment]:
        """Get all pending split payments (for processing via Celery)."""
        return (
            self.db.query(SplitPayment)
            .filter(SplitPayment.status == SplitStatus.PENDING)
            .all()
        )

    def get_splits_by_recipient(self, recipient_id: str) -> List[SplitPayment]:
        """Get all split payments for a specific recipient."""
        return (
            self.db.query(SplitPayment)
            .filter(SplitPayment.recipient_id == recipient_id)
            .all()
        )
