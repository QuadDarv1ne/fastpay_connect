"""Payments routes for API v2.

Improvements over v1:
- Proper Pydantic v2 response models
- Idempotency key support for safe retries
- Metadata attachment to payments
- Structured error responses
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies import get_payment_repository
from app.middleware.rate_limiter import limiter
from app.repositories.payment_repository import PaymentRepository
from app.schemas.v2 import (IdempotencyResponse, PaymentCreateRequest,
                            PaymentResponse, PaymentStatusEnum,
                            PaymentStatusResponse)
from app.services.payment_service import PaymentService, PaymentServiceError

router = APIRouter()

VALID_GATEWAYS = (
    "yookassa", "tinkoff", "cloudpayments", "unitpay", "robokassa",
    "sbp", "rustore", "apple_pay", "google_pay",
)

# In-memory idempotency store (production should use Redis)
# Each entry stores (data, expires_at) to allow TTL-based cleanup
_idempotency_store: Dict[str, Dict[str, Any]] = {}
_IDEMPOTENCY_TTL = timedelta(hours=24)


def _cleanup_expired_idempotency_entries() -> None:
    """Remove expired entries from the idempotency store."""
    now = datetime.now(timezone.utc)
    expired_keys = [
        k for k, v in _idempotency_store.items()
        if v.get("expires_at", now) < now
    ]
    for k in expired_keys:
        _idempotency_store.pop(k, None)


@router.post("/create", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("200/hour")
async def create_payment_v2(
    request: Request,
    payment_data: PaymentCreateRequest,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> PaymentResponse:
    """Create a new payment (v2).

    Supports idempotency via `idempotency_key` — duplicate requests
    with the same key return the original result without re-processing.
    """
    # Periodic cleanup of expired entries
    _cleanup_expired_idempotency_entries()

    # Idempotency check
    if payment_data.idempotency_key:
        key = f"idem:{payment_data.idempotency_key}"
        stored = _idempotency_store.get(key)
        if stored and stored.get("expires_at", datetime.min.replace(tzinfo=timezone.utc)) > datetime.now(timezone.utc):
            original = stored
            return PaymentResponse(
                success=True,
                payment_id=original.get("payment_id"),
                order_id=original["order_id"],
                amount=original["amount"],
                currency=original["currency"],
                status=PaymentStatusEnum(original.get("status", "pending")),
                payment_url=original.get("payment_url"),
                message="Idempotent replay — original request result returned",
            )

    gateway = payment_data.gateway
    if gateway not in VALID_GATEWAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": f"Unknown gateway: {gateway}. Valid options: {', '.join(VALID_GATEWAYS)}",
                "order_id": payment_data.order_id or "unknown",
            },
        )

    # Build v1-compatible PaymentRequest
    from app.schemas import PaymentRequest
    v1_data = PaymentRequest(
        order_id=payment_data.order_id,
        gateway=gateway,
        amount=payment_data.amount,
        currency=payment_data.currency,
        description=payment_data.description,
    )

    service = PaymentService(repository)
    try:
        result = await service.create_payment(v1_data)
    except PaymentServiceError as e:
        error_msg = str(e)
        order_id = getattr(e, "order_id", None) or payment_data.order_id or "unknown"
        if "not configured" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": error_msg, "order_id": order_id},
            )
        elif "timeout" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail={"error": error_msg, "order_id": order_id},
            )
        elif "unavailable" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": error_msg, "order_id": order_id},
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": error_msg, "order_id": order_id},
        )

    # Store idempotency result with TTL
    if payment_data.idempotency_key:
        key = f"idem:{payment_data.idempotency_key}"
        _idempotency_store[key] = {
            "payment_id": result.payment_id,
            "order_id": result.order_id,
            "amount": result.amount,
            "currency": result.currency or "RUB",
            "status": "processing",
            "payment_url": result.payment_url,
            "expires_at": datetime.now(timezone.utc) + _IDEMPOTENCY_TTL,
        }

    return PaymentResponse(
        success=True,
        payment_id=result.payment_id,
        order_id=result.order_id,
        amount=result.amount,
        currency=result.currency or "RUB",
        status=PaymentStatusEnum.PROCESSING,
        payment_url=result.payment_url,
        message="Payment created successfully",
    )


@router.get("/{order_id}", response_model=PaymentStatusResponse)
@limiter.limit("300/hour")
async def get_payment_status_v2(
    request: Request,
    order_id: str,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> PaymentStatusResponse:
    """Get detailed payment status by order_id (v2)."""
    payment = repository.get_by_order_id(order_id)

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Payment not found", "order_id": order_id},
        )

    return PaymentStatusResponse(
        order_id=payment.order_id,
        payment_id=payment.payment_id,
        status=PaymentStatusEnum(
            payment.status.value if hasattr(payment.status, "value") else str(payment.status)
        ),
        amount=payment.amount,
        currency=payment.currency or "RUB",
        payment_gateway=payment.payment_gateway,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
        metadata=payment.metadata_json,
    )


@router.post(
    "/{order_id}/idempotency",
    response_model=IdempotencyResponse,
    summary="Check idempotency status",
)
@limiter.limit("300/hour")
async def check_idempotency_v2(
    request: Request,
    order_id: str,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> IdempotencyResponse:
    """Check if a payment with this order_id already exists (idempotency probe)."""
    payment = repository.get_by_order_id(order_id)

    if payment:
        return IdempotencyResponse(
            is_duplicate=True,
            original_payment_id=payment.payment_id,
        )

    return IdempotencyResponse(is_duplicate=False)
