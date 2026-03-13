"""Payments routes for API v1."""

from fastapi import APIRouter, Depends, Request
from typing import Dict, Any

from app.dependencies import get_payment_repository
from app.repositories.payment_repository import PaymentRepository
from app.schemas import PaymentRequest, PaymentResponse
from app.middleware.rate_limiter import limiter

router = APIRouter()


@router.post("/create", response_model=PaymentResponse)
@limiter.limit("100/hour")
async def create_payment_v1(
    request: Request,
    payment_data: PaymentRequest,
    repository: PaymentRepository = Depends(get_payment_repository),
) -> PaymentResponse:
    """Create a new payment (v1)."""
    from app.services.payment_service import PaymentService
    from app.settings import settings
    
    service = PaymentService(repository, settings)
    return await service.create_payment(payment_data)


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
        return {"error": "Payment not found", "order_id": order_id}
    
    return {
        "order_id": payment.order_id,
        "payment_id": payment.payment_id,
        "status": payment.status.value if hasattr(payment.status, 'value') else str(payment.status),
        "amount": payment.amount,
        "currency": payment.currency,
        "payment_gateway": payment.payment_gateway,
    }
