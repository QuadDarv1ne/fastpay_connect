"""Роуты для работы с платежами."""

import logging
from fastapi import APIRouter, Depends, Request, HTTPException, status
from app.schemas import PaymentRequest, PaymentResponse
from app.dependencies import get_payment_repository
from app.repositories.payment_repository import PaymentRepository
from app.middleware.rate_limiter import limiter
from app.services.payment_service import PaymentService, PaymentServiceError

logger = logging.getLogger(__name__)

router = APIRouter()


def _create_payment_handler(gateway: str):
    """Создание обработчика для конкретного платёжного шлюза."""

    async def handler(
        request: Request,
        payment_request: PaymentRequest,
        repository: PaymentRepository = Depends(get_payment_repository),
    ) -> PaymentResponse:
        service = PaymentService(repository)
        try:
            return await service.create_payment(payment_request, gateway_key=gateway)
        except PaymentServiceError as e:
            error_msg = str(e)
            order_id = getattr(e, "order_id", None) or payment_request.order_id or "unknown"
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

    return limiter.limit("10/minute")(handler)


router.post("/yookassa", response_model=PaymentResponse)(
    _create_payment_handler("yookassa")
)
router.post("/tinkoff", response_model=PaymentResponse)(
    _create_payment_handler("tinkoff")
)
router.post("/cloudpayments", response_model=PaymentResponse)(
    _create_payment_handler("cloudpayments")
)
router.post("/unitpay", response_model=PaymentResponse)(
    _create_payment_handler("unitpay")
)
router.post("/robokassa", response_model=PaymentResponse)(
    _create_payment_handler("robokassa")
)
