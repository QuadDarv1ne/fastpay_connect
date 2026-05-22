"""Payments routes for API v1."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Dict, Any

from app.dependencies import get_payment_repository
from app.repositories.payment_repository import PaymentRepository
from app.schemas import PaymentRequest, PaymentResponse
from app.middleware.rate_limiter import limiter
from app.services.payment_service import PaymentService, PaymentServiceError

router = APIRouter()

VALID_GATEWAYS = ("yookassa", "tinkoff", "cloudpayments", "unitpay", "robokassa", "sbp", "rustore", "apple_pay", "google_pay")


@router.post("/create", response_model=PaymentResponse)
@limiter.limit("100/hour")
async def create_payment_v1(
    request: Request,
    payment_data: PaymentRequest,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> PaymentResponse:
    """Create a new payment (v1)."""
    gateway = payment_data.gateway or "yookassa"
    if gateway not in VALID_GATEWAYS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": f"Unknown gateway: {gateway}. Valid options: {', '.join(VALID_GATEWAYS)}",
                "order_id": payment_data.order_id or "unknown",
            },
        )

    service = PaymentService(repository)
    try:
        return await service.create_payment(payment_data)
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


@router.get("/status/{order_id}")
@limiter.limit("200/hour")
async def get_payment_status_v1(
    request: Request,
    order_id: str,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> Dict[str, Any]:
    """Get payment status by order_id (v1)."""
    payment = repository.get_by_order_id(order_id)
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Payment not found", "order_id": order_id},
        )
    
    return {
        "order_id": payment.order_id,
        "payment_id": payment.payment_id,
        "status": payment.status.value if hasattr(payment.status, 'value') else str(payment.status),
        "amount": payment.amount,
        "currency": payment.currency,
        "payment_gateway": payment.payment_gateway,
    }
