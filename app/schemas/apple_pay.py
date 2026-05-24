"""Схемы Pydantic для Apple Pay."""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class ApplePayNetworkEnum(str, Enum):
    """Платёжные сети Apple Pay."""
    VISA = "visa"
    MASTERCARD = "masterCard"
    AMEX = "amex"
    DISCOVER = "discover"
    ELO = "elo"
    JCB = "jcb"
    CARTES_BANCAIRES = "cartesBancaires"
    INTERAC = "interac"
    ELECTRON = "electron"


class ApplePayStatusEnum(str, Enum):
    """Статусы платежей Apple Pay."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIAL_REFUNDED = "partial_refunded"


class ApplePayPaymentRequest(BaseModel):
    """Запрос на создание платежа Apple Pay."""
    amount: float = Field(..., gt=0, le=1000000, description="Сумма платежа")
    order_id: str = Field(..., max_length=100, description="ID заказа")
    description: str = Field(default="", max_length=500, description="Описание платежа")
    currency: str = Field(default="RUB", max_length=3, description="Валюта платежа (ISO 4217)")
    country_code: str = Field(default="RU", max_length=2, description="Код страны (ISO 3166-1)")
    supported_networks: Optional[List[ApplePayNetworkEnum]] = Field(
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


class ApplePayPaymentSessionRequest(BaseModel):
    """Запрос на создание сессии Apple Pay."""
    order_id: str = Field(..., max_length=100, description="ID заказа")
    amount: float = Field(..., gt=0, le=1000000, description="Сумма платежа")
    description: str = Field(default="", max_length=500, description="Описание платежа")
    currency: str = Field(default="RUB", max_length=3, description="Валюта платежа")
    domain_name: str = Field(..., description="Доменное имя для валидации")


class ApplePayTokenRequest(BaseModel):
    """Запрос на обработку токена Apple Pay."""
    order_id: str = Field(..., max_length=100, description="ID заказа")
    amount: float = Field(..., gt=0, description="Сумма платежа")
    currency: str = Field(default="RUB", max_length=3, description="Валюта платежа")
    token_data: Dict[str, Any] = Field(..., description="Токен от Apple Pay (paymentData)")


class ApplePayPaymentResponse(BaseModel):
    """Ответ для платежа Apple Pay."""
    success: bool = True
    payment_id: Optional[str] = None
    order_id: str
    amount: float
    currency: str
    status: ApplePayStatusEnum = ApplePayStatusEnum.PENDING
    payment_url: Optional[str] = None
    session_data: Optional[str] = None
    merchant_id: Optional[str] = None
    message: str = ""


class ApplePayPaymentInfoResponse(BaseModel):
    """Информация о платеже Apple Pay."""
    payment_id: str
    order_id: str
    amount: float
    currency: str
    status: ApplePayStatusEnum
    card_network: Optional[str] = None
    transaction_id: Optional[str] = None
    created_at: Optional[str] = None
    processed_at: Optional[str] = None


class ApplePayRefundRequest(BaseModel):
    """Запрос на возврат платежа Apple Pay."""
    payment_id: str = Field(..., description="ID платежа")
    amount: Optional[float] = Field(None, gt=0, description="Сумма возврата (полная если не указана)")
    reason: str = Field(default="", max_length=500, description="Причина возврата")


class ApplePayRefundResponse(BaseModel):
    """Ответ на возврат платежа Apple Pay."""
    success: bool
    refund_id: str
    payment_id: str
    amount: float
    status: str
    message: str


class ApplePayWebhookPayload(BaseModel):
    """Webhook уведомление от Apple Pay."""
    event_type: str = Field(..., description="Тип события")
    order_id: str = Field(..., description="ID заказа")
    payment_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = "RUB"
    status: Optional[ApplePayStatusEnum] = None
    timestamp: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ApplePayWebhookResponse(BaseModel):
    """Ответ на webhook Apple Pay."""
    status: str
    order_id: str
    event_type: str
    processed_at: str


class ApplePayMerchantValidationRequest(BaseModel):
    """Запрос на валидацию мерчанта Apple Pay."""
    domain_name: str = Field(..., description="Доменное имя для валидации")
    display_name: str = Field(default="FastPay Connect", description="Отображаемое имя мерчанта")


class ApplePayMerchantValidationResponse(BaseModel):
    """Ответ на валидацию мерчанта Apple Pay."""
    merchant_id: str
    domain_name: str
    environment: str
    status: str
    expires_at: str


class ApplePayBanksResponse(BaseModel):
    """Список поддерживаемых банков (для совместимости с другими шлюзами)."""
    banks: List[Dict[str, str]] = Field(default_factory=list)
    supported_networks: List[str] = Field(
        default=["visa", "masterCard", "amex", "discover"]
    )
