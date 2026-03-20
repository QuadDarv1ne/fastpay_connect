"""Схемы Pydantic для Google Pay."""

from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, List, Dict, Any
from enum import Enum


class GooglePayNetworkEnum(str, Enum):
    """Платёжные сети Google Pay."""
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"
    AMEX = "AMEX"
    DISCOVER = "DISCOVER"
    JCB = "JCB"
    INTERAC = "INTERAC"
    ELO = "ELO"


class GooglePayCardClassEnum(str, Enum):
    """Классы карт Google Pay."""
    UNSPECIFIED = "UNSPECIFIED"
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"
    PREPAID = "PREPAID"


class GooglePayStatusEnum(str, Enum):
    """Статусы платежей Google Pay."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIAL_REFUNDED = "partial_refunded"


class GooglePayEnvironmentEnum(str, Enum):
    """Окружение Google Pay."""
    TEST = "TEST"
    PRODUCTION = "PRODUCTION"


class GooglePayPaymentRequest(BaseModel):
    """Запрос на создание платежа Google Pay."""
    amount: float = Field(..., gt=0, le=1000000, description="Сумма платежа")
    order_id: str = Field(..., max_length=100, description="ID заказа")
    description: str = Field(default="", max_length=500, description="Описание платежа")
    currency: str = Field(default="RUB", max_length=3, description="Валюта платежа (ISO 4217)")
    country_code: str = Field(default="RU", max_length=2, description="Код страны (ISO 3166-1)")
    supported_networks: Optional[List[GooglePayNetworkEnum]] = Field(
        default=None, description="Поддерживаемые платёжные сети"
    )
    email: Optional[EmailStr] = Field(None, description="Email для уведомлений")

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Сумма должна быть больше 0')
        if v > 1000000:
            raise ValueError('Сумма не может превышать 1 000 000')
        return round(v, 2)

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if len(v) != 3:
            raise ValueError('Валюта должна быть 3-символьным кодом ISO 4217')
        return v.upper()

    @field_validator('country_code')
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        if len(v) != 2:
            raise ValueError('Код страны должен быть 2-символьным (ISO 3166-1)')
        return v.upper()


class GooglePayPaymentDataRequest(BaseModel):
    """Запрос на создание платежных данных Google Pay."""
    order_id: str = Field(..., max_length=100, description="ID заказа")
    amount: float = Field(..., gt=0, le=1000000, description="Сумма платежа")
    description: str = Field(default="", max_length=500, description="Описание платежа")
    currency: str = Field(default="RUB", max_length=3, description="Валюта платежа")
    merchant_name: str = Field(default="FastPay Connect", description="Название мерчанта")
    supported_networks: Optional[List[GooglePayNetworkEnum]] = Field(
        default=None, description="Поддерживаемые платёжные сети"
    )


class GooglePayTokenRequest(BaseModel):
    """Запрос на обработку токена Google Pay."""
    order_id: str = Field(..., max_length=100, description="ID заказа")
    amount: float = Field(..., gt=0, description="Сумма платежа")
    currency: str = Field(default="RUB", max_length=3, description="Валюта платежа")
    token_data: Dict[str, Any] = Field(..., description="Токен от Google Pay")


class GooglePayPaymentResponse(BaseModel):
    """Ответ для платежа Google Pay."""
    success: bool = True
    payment_id: Optional[str] = None
    order_id: str
    amount: float
    currency: str
    status: GooglePayStatusEnum = GooglePayStatusEnum.PENDING
    payment_url: Optional[str] = None
    payment_data_request: Optional[str] = None
    merchant_id: Optional[str] = None
    environment: Optional[str] = None
    message: str = ""


class GooglePayPaymentInfoResponse(BaseModel):
    """Информация о платеже Google Pay."""
    payment_id: str
    order_id: str
    amount: float
    currency: str
    status: GooglePayStatusEnum
    card_network: Optional[str] = None
    card_details: Optional[str] = None
    transaction_id: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[str] = None
    processed_at: Optional[str] = None


class GooglePayRefundRequest(BaseModel):
    """Запрос на возврат платежа Google Pay."""
    payment_id: str = Field(..., description="ID платежа")
    amount: Optional[float] = Field(None, gt=0, description="Сумма возврата (полная если не указана)")
    reason: str = Field(default="", max_length=500, description="Причина возврата")


class GooglePayRefundResponse(BaseModel):
    """Ответ на возврат платежа Google Pay."""
    success: bool
    refund_id: str
    payment_id: str
    amount: float
    status: str
    message: str


class GooglePayWebhookPayload(BaseModel):
    """Webhook уведомление от Google Pay."""
    event_type: str = Field(..., description="Тип события")
    order_id: str = Field(..., description="ID заказа")
    payment_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = "RUB"
    status: Optional[GooglePayStatusEnum] = None
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class GooglePayWebhookResponse(BaseModel):
    """Ответ на webhook Google Pay."""
    status: str
    order_id: str
    event_type: str
    processed_at: str


class GooglePayMerchantValidationResponse(BaseModel):
    """Ответ на валидацию мерчанта Google Pay."""
    merchant_id: str
    gateway_id: Optional[str] = None
    environment: str
    status: str
    expires_at: str


class GooglePayIsReadyToPayResponse(BaseModel):
    """Ответ на проверку готовности Google Pay."""
    result: bool = Field(..., description="Готов ли пользователь к оплате")
    card_networks: Optional[List[str]] = Field(
        default=None, description="Доступные платёжные сети"
    )
