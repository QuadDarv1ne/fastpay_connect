import enum
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (Column, DateTime, Enum, ForeignKey, Index, Integer,
                        Numeric, String, Text)
from sqlalchemy.orm import relationship

from app.database import Base

logger = logging.getLogger(__name__)


class PaymentStatus(enum.Enum):
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
        Index('ix_order_id', 'order_id'),
        Index('ix_tenant_id', 'tenant_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'), index=True, nullable=True)
    order_id = Column(String, unique=True, index=True, nullable=False)
    payment_id = Column(String, index=True)
    transaction_id = Column(String, index=True)
    payment_gateway = Column(String, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="RUB")
    status = Column(Enum(PaymentStatus, values_callable=lambda x: [e.value for e in x]), default=PaymentStatus.PENDING, index=True)
    description = Column(String)
    payment_url = Column(String)
    metadata_json = Column(String)
    webhook_processed = Column(Text, default="[]")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Связь с tenant
    tenant = relationship("Tenant", backref="payments")

    def __repr__(self) -> str:
        return f"<Payment(order_id={self.order_id}, amount={self.amount}, status={self.status})>"

    def _get_processed_events(self) -> List[str]:
        """Get list of processed webhook event IDs."""
        if not self.webhook_processed or self.webhook_processed == "[]":
            return []
        try:
            return json.loads(self.webhook_processed)
        except (json.JSONDecodeError, TypeError):
            return [e for e in self.webhook_processed.split(",") if e]

    def _parse_metadata(self) -> Any:
        """Safely parse metadata_json, returning raw string on invalid JSON."""
        try:
            return json.loads(self.metadata_json)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Invalid metadata_json for payment {self.id}: {self.metadata_json[:100]}")
            return self.metadata_json

    def _set_processed_events(self, events: List[str]) -> None:
        """Set list of processed webhook event IDs as JSON."""
        self.webhook_processed = json.dumps(events)

    def is_webhook_processed(self, event_id: str) -> bool:
        """Проверка, был ли уже обработан webhook с данным event_id."""
        return event_id in self._get_processed_events()

    def mark_webhook_processed(self, event_id: str) -> None:
        """Отметить webhook событие как обработанное."""
        events = self._get_processed_events()
        if event_id not in events:
            events.append(event_id)
            self._set_processed_events(events)

    def to_dict(self) -> Dict[str, Any]:
        """Конвертация платежа в словарь."""
        return {
            "id": self.id,
            "order_id": self.order_id,
            "payment_id": self.payment_id,
            "transaction_id": self.transaction_id,
            "payment_gateway": self.payment_gateway,
            "amount": self.amount,
            "currency": self.currency,
            "status": self.status.value if isinstance(self.status, PaymentStatus) else self.status,
            "description": self.description,
            "payment_url": self.payment_url,
            "metadata": self._parse_metadata() if self.metadata_json else None,
            "webhook_processed": self._get_processed_events(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
