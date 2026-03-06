from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Index
from datetime import datetime, timezone
from typing import Dict, Any
from app.database import Base
import enum
import json


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
    __table_args__ = (
        Index('ix_status_created', 'status', 'created_at'),
        Index('ix_gateway_status', 'payment_gateway', 'status'),
        Index('ix_transaction_id', 'transaction_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String, unique=True, index=True, nullable=False)
    payment_id = Column(String, index=True)
    transaction_id = Column(String, index=True)  # ID транзакции от платёжной системы
    payment_gateway = Column(String, nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="RUB")
    status = Column(String, default=PaymentStatus.PENDING.value, index=True)
    description = Column(String)
    payment_url = Column(String)
    metadata_json = Column(String)
    webhook_processed = Column(String, default="")  # Список уже обработанных webhook event_id
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Payment(order_id={self.order_id}, amount={self.amount}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert payment to dictionary."""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "payment_id": self.payment_id,
            "transaction_id": self.transaction_id,
            "payment_gateway": self.payment_gateway,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status,
            "description": self.description,
            "payment_url": self.payment_url,
            "metadata": json.loads(self.metadata_json) if self.metadata_json else None,
            "webhook_processed": self.webhook_processed.split(",") if self.webhook_processed else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
