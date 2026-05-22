"""Split payment routes for marketplace support.

Provides endpoints for creating and managing split payments
where a single payment is distributed among multiple recipients.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import List, Dict, Any
from decimal import Decimal

from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.split_payment import (
    SplitPaymentCreateRequest,
    SplitPaymentResponse,
    SplitPaymentStatusResponse,
    SplitPaymentRefundRequest,
)
from app.services.split_payment_service import SplitPaymentService, SplitPaymentError
from app.middleware.rate_limiter import limiter

router = APIRouter()


@router.post("/split", response_model=SplitPaymentResponse)
@limiter.limit("50/hour")
async def create_split_payment(
    request: Request,
    split_data: SplitPaymentCreateRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Create a split payment for marketplace distribution.

    The sum of all recipient amounts must equal the total_amount.
    """
    service = SplitPaymentService(db)
    try:
        payment = service.create_split_payment(split_data)
        splits = service.get_split_payments(payment.order_id)

        return {
            "order_id": payment.order_id,
            "total_amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status.value if hasattr(payment.status, "value") else str(payment.status),
            "splits": [s.to_dict() for s in splits],
            "created_at": payment.created_at.isoformat() if payment.created_at else None,
            "gateway": payment.payment_gateway,
        }
    except SplitPaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e), "order_id": e.order_id or "unknown"},
        )


@router.get("/split/{order_id}", response_model=SplitPaymentStatusResponse)
@limiter.limit("200/hour")
async def get_split_payment_status(
    request: Request,
    order_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get split payment status and distribution details."""
    service = SplitPaymentService(db)
    splits = service.get_split_payments(order_id)

    if not splits:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Split payment not found", "order_id": order_id},
        )

    return {
        "order_id": order_id,
        "splits": [s.to_dict() for s in splits],
    }


@router.post("/split/{split_id}/refund")
@limiter.limit("20/hour")
async def refund_split_payment(
    request: Request,
    split_id: int,
    refund_data: SplitPaymentRefundRequest,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Refund a specific split payment distribution."""
    service = SplitPaymentService(db)
    try:
        split = service.refund_split_payment(
            split_id=split_id,
            amount=refund_data.amount,
            reason=refund_data.reason,
        )
        return {
            "status": "refunded",
            "split_id": split.id,
            "amount": float(split.amount),
            "currency": split.currency,
        }
    except SplitPaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)},
        )


@router.get("/split/recipient/{recipient_id}")
@limiter.limit("100/hour")
async def get_splits_by_recipient(
    request: Request,
    recipient_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get all split payments for a specific recipient."""
    service = SplitPaymentService(db)
    splits = service.get_splits_by_recipient(recipient_id)

    return {
        "recipient_id": recipient_id,
        "count": len(splits),
        "splits": [s.to_dict() for s in splits],
    }


@router.get("/split/pending")
@limiter.limit("50/hour")
async def get_pending_splits(
    request: Request,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get all pending split payments (for processing)."""
    service = SplitPaymentService(db)
    splits = service.get_pending_splits()

    return {
        "count": len(splits),
        "splits": [s.to_dict() for s in splits],
    }
