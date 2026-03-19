"""RuStore Pay SDK API endpoints."""

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.middleware.rate_limiter import limiter

router = APIRouter(prefix="/rustore", tags=["RuStore"])


class ValidatePurchaseRequest(BaseModel):
    """Запрос на валидацию покупки."""
    invoice_id: str
    expected_amount: Optional[float] = None
    product_id: Optional[str] = None


class ValidateSubscriptionRequest(BaseModel):
    """Запрос на валидацию подписки."""
    purchase_id: str


class ConfirmPurchaseRequest(BaseModel):
    """Запрос на подтверждение покупки."""
    invoice_id: str


class CancelPurchaseRequest(BaseModel):
    """Запрос на отмену покупки."""
    invoice_id: str


@router.post("/validate")
@limiter.limit("100/hour")
async def validate_purchase(
    request: Request,
    data: ValidatePurchaseRequest,
) -> Dict[str, Any]:
    """Валидация покупки после оплаты в приложении.
    
    Args:
        invoice_id: Идентификатор счёта из RuStore SDK
        expected_amount: Ожидаемая сумма для проверки (опционально)
        product_id: Идентификатор продукта (опционально)
    
    Returns:
        Результат валидации с информацией о покупке
    """
    from app.payment_gateways.rustore import gateway
    
    try:
        result = await gateway.validate_purchase(
            invoice_id=data.invoice_id,
            expected_amount=data.expected_amount
        )
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate-subscription")
@limiter.limit("100/hour")
async def validate_subscription(
    request: Request,
    data: ValidateSubscriptionRequest,
) -> Dict[str, Any]:
    """Валидация активной подписки.
    
    Args:
        purchase_id: Идентификатор покупки подписки
    
    Returns:
        Результат валидации подписки
    """
    from app.payment_gateways.rustore import gateway
    
    try:
        result = await gateway.validate_subscription(data.purchase_id)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/confirm")
@limiter.limit("100/hour")
async def confirm_purchase(
    request: Request,
    data: ConfirmPurchaseRequest,
) -> Dict[str, Any]:
    """Подтверждение двухстадийной покупки.
    
    Args:
        invoice_id: Идентификатор счёта для подтверждения
    
    Returns:
        Результат подтверждения
    """
    from app.payment_gateways.rustore import gateway
    
    try:
        result = await gateway.confirm_purchase(data.invoice_id)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cancel")
@limiter.limit("100/hour")
async def cancel_purchase(
    request: Request,
    data: CancelPurchaseRequest,
) -> Dict[str, Any]:
    """Отмена двухстадийной покупки.
    
    Args:
        invoice_id: Идентификатор счёта для отмены
    
    Returns:
        Результат отмены
    """
    from app.payment_gateways.rustore import gateway
    
    try:
        result = await gateway.cancel_purchase(data.invoice_id)
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/purchases/{user_id}")
@limiter.limit("200/hour")
async def get_user_purchases(
    request: Request,
    user_id: str,
) -> Dict[str, Any]:
    """Получение списка покупок пользователя.
    
    Args:
        user_id: Идентификатор пользователя (appUserId из SDK)
    
    Returns:
        Список покупок пользователя
    """
    from app.payment_gateways.rustore import gateway
    
    return await gateway.get_user_purchases(user_id)


@router.get("/subscriptions/{user_id}")
@limiter.limit("200/hour")
async def get_user_subscriptions(
    request: Request,
    user_id: str,
) -> Dict[str, Any]:
    """Получение списка подписок пользователя.
    
    Args:
        user_id: Идентификатор пользователя (appUserId из SDK)
    
    Returns:
        Список подписок пользователя
    """
    from app.payment_gateways.rustore import gateway
    
    return await gateway.get_user_subscriptions(user_id)


@router.get("/products")
@limiter.limit("200/hour")
async def get_products(
    request: Request,
    product_ids: Optional[str] = None,
) -> Dict[str, Any]:
    """Получение списка продуктов из RuStore.
    
    Args:
        product_ids: Список идентификаторов продуктов через запятую (опционально)
    
    Returns:
        Список продуктов с информацией о ценах
    """
    from app.payment_gateways.rustore import gateway
    
    product_ids_list = None
    if product_ids:
        product_ids_list = [pid.strip() for pid in product_ids.split(",")]
    
    return await gateway.get_products(product_ids_list)
