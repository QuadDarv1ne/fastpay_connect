from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from datetime import datetime, timezone
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
    payment_id = Column(String, index=True)
    payment_gateway = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="RUB")
    status = Column(String, default=PaymentStatus.PENDING.value)
    description = Column(String)
    payment_url = Column(String)
    metadata_json = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Payment(order_id={self.order_id}, amount={self.amount}, status={self.status})>"
