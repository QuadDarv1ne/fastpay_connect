from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from datetime import datetime
from app.database import Base
import enum


class PaymentStatus(str, enum.Enum):
    """Статусы платежа."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class Payment(Base):
    """Модель для хранения информации о платежах."""
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True, nullable=False)
    payment_id = Column(String, index=True)  # ID от платёжной системы
    payment_gateway = Column(String, nullable=False)  # yookassa, tinkoff, etc.
    amount = Column(Float, nullable=False)
    currency = Column(String, default="RUB")
    status = Column(String, default=PaymentStatus.PENDING.value)
    description = Column(String)
    payment_url = Column(String)  # Ссылка на оплату
    metadata_json = Column(String)  # Дополнительные данные в JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Payment(order_id={self.order_id}, amount={self.amount}, status={self.status})>"
