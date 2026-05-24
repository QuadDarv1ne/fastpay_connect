from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class PaymentStatusEnum(str, Enum):
    """Статусы платежа для валидации."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class CurrencyEnum(str, Enum):
    """Поддерживаемые валюты (ISO 4217)."""
    RUB = "RUB"  # Российский рубль
    USD = "USD"  # Доллар США
    EUR = "EUR"  # Евро
    KZT = "KZT"  # Казахстанский тенге
    BYN = "BYN"  # Белорусский рубль
    CNY = "CNY"  # Китайский юань
    TRY = "TRY"  # Турецкая лира
    AED = "AED"  # Дирхам ОАЭ
    GBP = "GBP"  # Британский фунт
    JPY = "JPY"  # Японская иена


class PaymentRequest(BaseModel):
    """Модель запроса для создания платежа."""
    amount: float = Field(..., gt=0, le=1000000, description="Сумма платежа")
    description: str = Field(..., min_length=1, max_length=500, description="Описание платежа")
    order_id: Optional[str] = Field(None, max_length=50, description="ID заказа (опционально)")
    email: Optional[EmailStr] = Field(None, description="Email для уведомлений")
    currency: Optional[CurrencyEnum] = Field(default=CurrencyEnum.RUB, description="Валюта платежа")
    gateway: Optional[str] = Field(default="yookassa", description="Платёжный шлюз (yookassa, tinkoff, cloudpayments, unitpay, robokassa)")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Сумма должна быть больше 0')
        if v > 1000000:
            raise ValueError('Сумма не может превышать 1 000 000')
        return round(v, 2)

    @field_validator('description')
    @classmethod
    def validate_description(cls, v):
        if not v.strip():
            raise ValueError('Описание не может быть пустым')
        return v.strip()


class PaymentResponse(BaseModel):
    """Модель ответа для платежа."""
    success: bool
    payment_id: Optional[str] = None
    payment_url: Optional[str] = None
    order_id: str
    amount: float
    message: str


class PaymentErrorResponse(BaseModel):
    """Модель ответа об ошибке платежа."""
    success: bool = False
    order_id: str
    error: str


class WebhookPayload(BaseModel):
    """Модель для webhook уведомления."""
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    status: PaymentStatusEnum
    amount: Optional[float] = None
    currency: Optional[str] = "RUB"
    transaction_id: Optional[str] = None


class BulkPaymentRequest(BaseModel):
    """Запрос на массовое создание платежей."""
    payments: List[PaymentRequest] = Field(..., min_length=1, max_length=100)

    @field_validator('payments')
    @classmethod
    def validate_payments_list(cls, v):
        if len(v) > 100:
            raise ValueError('Максимум 100 платежей в одном запросе')
        return v
