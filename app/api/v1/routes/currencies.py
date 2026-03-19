"""Currency API endpoints."""

from fastapi import APIRouter, Depends, Request, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.middleware.rate_limiter import limiter
from app.utils.currency import (
    Currency,
    CurrencyService,
    CURRENCY_SYMBOLS,
    get_currency_service,
)

router = APIRouter(prefix="/currencies", tags=["Currencies"])


class CurrencyRateResponse(BaseModel):
    """Ответ с курсом валюты."""
    currency: str
    rate: float
    symbol: str
    name: str


class CurrencyListResponse(BaseModel):
    """Ответ со списком валют."""
    currencies: List[CurrencyRateResponse]
    last_updated: Optional[datetime] = None


from pydantic import BaseModel


class ConvertRequest(BaseModel):
    """Запрос на конвертацию валюты."""
    amount: float = Field(..., gt=0, description="Сумма для конвертации")
    from_currency: str = Field(..., description="Исходная валюта (ISO код)")
    to_currency: str = Field(..., description="Целевая валюта (ISO код)")


class ConvertResponse(BaseModel):
    """Ответ конвертации."""
    amount: float
    from_currency: str
    to_currency: str
    result: float
    rate: float
    formatted: str


@router.get("/", response_model=CurrencyListResponse)
@limiter.limit("100/hour")
async def list_currencies(
    request: Request,
    service: CurrencyService = Depends(get_currency_service),
) -> CurrencyListResponse:
    """
    Получить список всех поддерживаемых валют с курсами.

    Возвращает все валюты ISO 4217, поддерживаемые системой,
    с текущими курсами к RUB.
    """
    rates = service.get_all_rates()
    last_updated = service.get_last_updated()

    currencies = []
    for code, rate in rates.items():
        try:
            currency = Currency(code)
            currencies.append(
                CurrencyRateResponse(
                    currency=code,
                    rate=rate,
                    symbol=CURRENCY_SYMBOLS.get(currency, code),
                    name=currency.name,
                )
            )
        except ValueError:
            continue

    return CurrencyListResponse(
        currencies=currencies,
        last_updated=last_updated,
    )


@router.get("/{currency_code}", response_model=Dict[str, Any])
@limiter.limit("200/hour")
async def get_currency_rate(
    request: Request,
    currency_code: str,
    service: CurrencyService = Depends(get_currency_service),
) -> Dict[str, Any]:
    """
    Получить курс конкретной валюты к RUB.
    """
    if not service.is_supported(currency_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Currency '{currency_code}' is not supported",
        )

    try:
        currency = Currency(currency_code)
        rate = service.get_rate(currency)
        symbol = CURRENCY_SYMBOLS.get(currency, currency_code)

        return {
            "currency": currency_code,
            "rate": rate,
            "symbol": symbol,
            "name": currency.name,
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/convert", response_model=ConvertResponse)
@limiter.limit("50/hour")
async def convert_currency(
    request: Request,
    data: ConvertRequest,
    service: CurrencyService = Depends(get_currency_service),
) -> ConvertResponse:
    """
    Конвертировать сумму из одной валюты в другую.

    Конвертация происходит через базовую валюту RUB.
    """
    # Валидация валют
    if not service.is_supported(data.from_currency):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Currency '{data.from_currency}' is not supported",
        )

    if not service.is_supported(data.to_currency):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Currency '{data.to_currency}' is not supported",
        )

    try:
        from_cur = Currency(data.from_currency)
        to_cur = Currency(data.to_currency)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Конвертация
    result = service.convert(data.amount, from_cur, to_cur)

    # Получаем курс для информации
    if from_cur == to_cur:
        rate = 1.0
    else:
        rate = service.get_rate(from_cur) / service.get_rate(to_cur)

    formatted = service.format_amount(result, to_cur)

    return ConvertResponse(
        amount=data.amount,
        from_currency=data.from_currency,
        to_currency=data.to_currency,
        result=result,
        rate=round(rate, 4),
        formatted=formatted,
    )


@router.get("/supported", response_model=List[str])
@limiter.limit("200/hour")
async def get_supported_currencies(
    request: Request,
    service: CurrencyService = Depends(get_currency_service),
) -> List[str]:
    """
    Получить список кодов поддерживаемых валют.
    """
    return [c.value for c in Currency]
