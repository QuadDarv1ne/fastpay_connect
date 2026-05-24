"""
Schemas for SBP (Система Быстрых Платежей).
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class SBPStatusEnum(str, Enum):
    """Статусы платежей СБП."""

    PENDING = "PENDING"  # Ожидает оплаты
    PAID = "PAID"  # Оплачен
    REJECTED = "REJECTED"  # Отклонён
    EXPIRED = "EXPIRED"  # Истёк срок действия
    REFUNDED = "REFUNDED"  # Возвращён
    PARTIAL_REFUNDED = "PARTIAL_REFUNDED"  # Частично возвращён


class SBPBankResponse(BaseModel):
    """Информация о банке СБП."""

    code: str
    name: str
    bic: str


class SBPBanksResponse(BaseModel):
    """Список банков СБП."""

    banks: List[SBPBankResponse]


class SBPPaymentRequest(BaseModel):
    """Запрос на создание платежа СБП."""

    amount: float = Field(..., gt=0, le=1000000, description="Сумма платежа в рублях")
    order_id: str = Field(..., max_length=50, description="ID заказа")
    description: str = Field(..., max_length=250, description="Описание платежа")
    phone: Optional[str] = Field(None, description="Номер телефона получателя")
    bank_bic: Optional[str] = Field(None, max_length=11, description="BIC код банка")
    expiration_minutes: int = Field(default=30, ge=5, le=1440, description="Время действия (мин)")

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Валидация номера телефона."""
        if v is None:
            return v

        # Очистка номера
        clean_phone = "".join(c for c in v if c.isdigit())

        # Проверка длины
        if len(clean_phone) < 10 or len(clean_phone) > 12:
            raise ValueError("Invalid phone number length")

        # Добавляем 7 если начинается с 8
        if clean_phone.startswith("8"):
            clean_phone = "7" + clean_phone[1:]

        # Проверка что начинается с 7
        if not clean_phone.startswith("7"):
            raise ValueError("Phone number must start with 7 or 8")

        return "+" + clean_phone


class SBPPaymentResponse(BaseModel):
    """Ответ после создания платежа СБП."""

    success: bool
    payment_id: str
    order_id: str
    amount: float
    currency: str
    status: str
    payment_url: Optional[str] = None
    qr_code: Optional[str] = None  # Base64 QR кода
    expires_at: Optional[str] = None
    message: str


class SBPPaymentInfoResponse(BaseModel):
    """Информация о платеже СБП."""

    payment_id: str
    order_id: str
    amount: float
    currency: str
    status: SBPStatusEnum
    phone: Optional[str] = None
    bank_bic: Optional[str] = None
    created_at: Optional[str] = None
    paid_at: Optional[str] = None
    expires_at: Optional[str] = None


class SBPRefundRequest(BaseModel):
    """Запрос на возврат платежа СБП."""

    payment_id: str = Field(..., description="ID платежа")
    amount: Optional[float] = Field(None, gt=0, description="Сумма возврата")
    reason: str = Field(default="Refund", max_length=250, description="Причина возврата")


class SBPRefundResponse(BaseModel):
    """Ответ после возврата платежа СБП."""

    success: bool
    refund_id: str
    payment_id: str
    amount: float
    status: str
    reason: str
    message: str


class SBPWebhookPayload(BaseModel):
    """Webhook уведомление от СБП."""

    event: str
    payment: dict
    timestamp: str


class SBPWebhookResponse(BaseModel):
    """Ответ на webhook уведомление."""

    status: str
    message: str
    event_type: Optional[str] = None
    payment_id: Optional[str] = None
    action: Optional[str] = None
