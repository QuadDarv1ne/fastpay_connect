from pydantic import BaseModel, Field, field_validator
from typing import Optional


class PaymentRequest(BaseModel):
    """Модель запроса для создания платежа."""
    amount: float = Field(..., gt=0, le=1000000, description="Сумма платежа")
    description: str = Field(..., min_length=1, max_length=500, description="Описание платежа")
    order_id: Optional[str] = Field(None, max_length=50, description="ID заказа (опционально)")

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


class WebhookPayload(BaseModel):
    """Модель для webhook уведомления."""
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    status: str
    amount: Optional[float] = None
    currency: Optional[str] = "RUB"
    transaction_id: Optional[str] = None

    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed = ['success', 'failed', 'pending', 'cancelled', 'refunded']
        if v.lower() not in allowed:
            raise ValueError(f'Недопустимый статус: {v}')
        return v.lower()
