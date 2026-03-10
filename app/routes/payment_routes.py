"""Роуты для работы с платежами."""

from typing import Any, Callable, Dict, Optional, Tuple
from fastapi import APIRouter, HTTPException, Depends, Request
from app.payment_gateways.yookassa import create_payment as yookassa_create
from app.payment_gateways.tinkoff import create_payment as tinkoff_create
from app.payment_gateways.cloudpayments import create_payment as cloudpayments_create
from app.payment_gateways.unitpay import create_payment as unitpay_create
from app.payment_gateways.robokassa import create_payment as robokassa_create
from app.schemas import PaymentRequest, PaymentResponse
from app.dependencies import get_payment_repository
from app.repositories.payment_repository import PaymentRepository
from app.middleware.rate_limiter import limiter
import uuid
import json
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

router = APIRouter()


@dataclass
class GatewayConfig:
    """Конфигурация платёжного шлюза."""

    name: str
    create_func: Callable
    payment_id_field: str
    payment_url_field: Optional[str] = None


GATEWAYS: Dict[str, GatewayConfig] = {
    "yookassa": GatewayConfig(
        name="yookassa",
        create_func=yookassa_create,
        payment_id_field="id",
        payment_url_field="confirmation.confirmation_url",
    ),
    "tinkoff": GatewayConfig(
        name="tinkoff",
        create_func=tinkoff_create,
        payment_id_field="payment_id",
        payment_url_field="payment_url",
    ),
    "cloudpayments": GatewayConfig(
        name="cloudpayments",
        create_func=cloudpayments_create,
        payment_id_field="transaction_id",
    ),
    "unitpay": GatewayConfig(
        name="unitpay",
        create_func=unitpay_create,
        payment_id_field="payment_id",
    ),
    "robokassa": GatewayConfig(
        name="robokassa",
        create_func=robokassa_create,
        payment_id_field="invoice_id",
    ),
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
    gateway: GatewayConfig,
    repository: PaymentRepository,
    amount: float,
    description: str,
    order_id: Optional[str] = None,
) -> Tuple[Dict[str, Any], Any]:
    """Обработка создания платежа."""
    order_id = order_id or generate_order_id()

    db_payment = repository.create(
        order_id=order_id,
        payment_gateway=gateway.name,
        amount=amount,
        description=description,
    )

    try:
        result = await gateway.create_func(amount, description, order_id)
    except Exception as e:
        logger.error(f"Payment gateway error: {e}")
        db_payment.status = "failed"
        db_payment.metadata_json = json.dumps({"error": str(e)})
        repository._db.commit()
        raise HTTPException(status_code=400, detail=f"Payment gateway error: {e}")

    if "error" in result:
        db_payment.status = "failed"
        db_payment.metadata_json = json.dumps({"error": result["error"]})
        repository._db.commit()
        raise HTTPException(status_code=400, detail=result["error"])

    payment_id = result.get(gateway.payment_id_field)
    payment_url = None
    if gateway.payment_url_field:
        payment_url = extract_nested_value(result, gateway.payment_url_field)

    db_payment.payment_id = payment_id
    db_payment.payment_url = payment_url
    db_payment.status = "processing"
    repository._db.commit()

    return result, db_payment


def create_payment_endpoint(gateway_key: str):
    """Создание endpoint для платёжного шлюза."""
    gateway = GATEWAYS[gateway_key]

    async def handler(
        request: Request,
        payment_request: PaymentRequest,
        repository: PaymentRepository = Depends(get_payment_repository),
    ) -> PaymentResponse:
        _, db_payment = await process_payment(
            gateway=gateway,
            repository=repository,
            amount=payment_request.amount,
            description=payment_request.description,
            order_id=payment_request.order_id,
        )

        return PaymentResponse(
            success=True,
            payment_id=db_payment.payment_id,
            payment_url=db_payment.payment_url,
            order_id=db_payment.order_id,
            amount=db_payment.amount,
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
