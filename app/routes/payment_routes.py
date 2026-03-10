"""Роуты для работы с платежами."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, status
from app.payment_gateways.yookassa import create_payment as yookassa_create
from app.payment_gateways.tinkoff import create_payment as tinkoff_create
from app.payment_gateways.cloudpayments import create_payment as cloudpayments_create
from app.payment_gateways.unitpay import create_payment as unitpay_create
from app.payment_gateways.robokassa import create_payment as robokassa_create
from app.payment_gateways.exceptions import (
    PaymentGatewayError,
    PaymentGatewayConfigError,
    PaymentGatewayTimeoutError,
    PaymentGatewayConnectionError,
)
from app.schemas import PaymentRequest, PaymentResponse
from app.dependencies import get_payment_repository
from app.repositories.payment_repository import PaymentRepository
from app.middleware.rate_limiter import limiter
from app.models.payment import PaymentStatus
import uuid
import json
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

GATEWAY_CONFIGS: Dict[str, Dict[str, Any]] = {
    "yookassa": {
        "name": "yookassa",
        "create_func": yookassa_create,
        "payment_id_field": "id",
        "payment_url_field": "confirmation.confirmation_url",
    },
    "tinkoff": {
        "name": "tinkoff",
        "create_func": tinkoff_create,
        "payment_id_field": "payment_id",
        "payment_url_field": "payment_url",
    },
    "cloudpayments": {
        "name": "cloudpayments",
        "create_func": cloudpayments_create,
        "payment_id_field": "transaction_id",
    },
    "unitpay": {
        "name": "unitpay",
        "create_func": unitpay_create,
        "payment_id_field": "payment_id",
    },
    "robokassa": {
        "name": "robokassa",
        "create_func": robokassa_create,
        "payment_id_field": "invoice_id",
    },
}


def generate_order_id() -> str:
    """Генерация уникального order_id."""
    return str(uuid.uuid4()).replace("-", "")[:12]


def extract_nested_value(data: Dict[str, Any], path: str) -> Optional[Any]:
    """Извлечение вложенного значения по пути."""
    keys = path.split(".")
    value = data
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None
    return value


async def process_payment(
    gateway_config: Dict[str, Any],
    repository: PaymentRepository,
    amount: float,
    description: str,
    order_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Обработка создания платежа."""
    order_id = order_id or generate_order_id()
    gateway_name = gateway_config["name"]

    db_payment = repository.create(
        order_id=order_id,
        payment_gateway=gateway_name,
        amount=amount,
        description=description,
    )

    create_func = gateway_config["create_func"]
    try:
        result = await create_func(amount, description, order_id)
    except PaymentGatewayConfigError as e:
        logger.error(f"Gateway config error: {e.message}")
        repository.update_status(
            order_id=order_id, status=PaymentStatus.FAILED, metadata={"error": e.message}
        )
        raise HTTPException(status_code=500, detail="Payment gateway not configured") from e
    except PaymentGatewayTimeoutError as e:
        logger.error(f"Gateway timeout: {e.message}")
        repository.update_status(
            order_id=order_id, status=PaymentStatus.FAILED, metadata={"error": "Gateway timeout"}
        )
        raise HTTPException(status_code=504, detail="Payment gateway timeout") from e
    except PaymentGatewayConnectionError as e:
        logger.error(f"Gateway connection error: {e.message}")
        repository.update_status(
            order_id=order_id, status=PaymentStatus.FAILED, metadata={"error": "Gateway connection failed"}
        )
        raise HTTPException(status_code=503, detail="Payment gateway unavailable") from e
    except PaymentGatewayError as e:
        logger.error(f"Gateway error: {e.message}")
        repository.update_status(
            order_id=order_id, status=PaymentStatus.FAILED, metadata={"error": e.message}
        )
        raise HTTPException(status_code=400, detail=e.message) from e

    if "error" in result:
        repository.update_status(
            order_id=order_id, status=PaymentStatus.FAILED, metadata={"error": result["error"]}
        )
        raise HTTPException(status_code=400, detail=result["error"])

    payment_id = result.get(gateway_config["payment_id_field"])
    payment_url = None
    if gateway_config.get("payment_url_field"):
        payment_url = extract_nested_value(result, gateway_config["payment_url_field"])

    repository.update_status(
        order_id=order_id,
        status=PaymentStatus.PROCESSING,
        metadata={"payment_id": payment_id, "payment_url": payment_url},
    )

    return {
        "payment_id": payment_id,
        "payment_url": payment_url,
        "order_id": order_id,
        "amount": amount,
    }


def create_payment_endpoint(gateway_key: str):
    """Создание endpoint для платёжного шлюза."""
    gateway_config = GATEWAY_CONFIGS[gateway_key]

    async def handler(
        request: Request,
        payment_request: PaymentRequest,
        repository: PaymentRepository = Depends(get_payment_repository),
    ) -> PaymentResponse:
        result = await process_payment(
            gateway_config=gateway_config,
            repository=repository,
            amount=payment_request.amount,
            description=payment_request.description,
            order_id=payment_request.order_id,
        )

        return PaymentResponse(
            success=True,
            payment_id=result["payment_id"],
            payment_url=result["payment_url"],
            order_id=result["order_id"],
            amount=result["amount"],
            message="Платёж успешно создан",
        )

    return limiter.limit("10/minute")(handler)


router.post("/yookassa", response_model=PaymentResponse)(
    create_payment_endpoint("yookassa")
)
router.post("/tinkoff", response_model=PaymentResponse)(
    create_payment_endpoint("tinkoff")
)
router.post("/cloudpayments", response_model=PaymentResponse)(
    create_payment_endpoint("cloudpayments")
)
router.post("/unitpay", response_model=PaymentResponse)(
    create_payment_endpoint("unitpay")
)
router.post("/robokassa", response_model=PaymentResponse)(
    create_payment_endpoint("robokassa")
)
