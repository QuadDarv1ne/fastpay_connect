"""
Webhook Event model для мониторинга retry queue.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, Index, JSON
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from app.database import Base
import enum
import json


class WebhookEventStatus(enum.Enum):
    """Статусы обработки webhook события."""
    PENDING = "pending"  # Ожидает обработки
    PROCESSING = "processing"  # В процессе
    SUCCESS = "success"  # Успешно обработано
    RETRY = "retry"  # Требуется повторная попытка
    FAILED = "failed"  # Обработка не удалась после всех попыток


class WebhookEvent(Base):
    """Модель для отслеживания webhook событий и retry попыток."""
    __tablename__ = 'webhook_events'
    __table_args__ = (
        Index('ix_webhook_gateway', 'gateway', 'created_at'),
        Index('ix_webhook_status', 'status'),
        Index('ix_webhook_order', 'order_id'),
        Index('ix_webhook_event_id', 'event_id', unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False)  # Уникальный ID события
    order_id = Column(String, index=True, nullable=False)  # ID заказа
    gateway = Column(String, nullable=False, index=True)  # Платёжная система
    status = Column(
        Enum(WebhookEventStatus),
        default=WebhookEventStatus.PENDING,
        index=True,
        nullable=False
    )
    
    # Retry информация
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=5, nullable=False)
    last_error = Column(Text, nullable=True)  # Последняя ошибка
    next_retry_at = Column(DateTime, nullable=True)  # Время следующей попытки
    
    # Payload и метаданные
    payload = Column(JSON, nullable=True)  # Исходный payload webhook
    metadata_json = Column(JSON, nullable=True)  # Дополнительные метаданные
    
    # Временные метки
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)  # Время успешной обработки

    def __repr__(self) -> str:
        return f"<WebhookEvent(event_id={self.event_id}, gateway={self.gateway}, status={self.status.value})>"

    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь."""
        return {
            "id": self.id,
            "event_id": self.event_id,
            "order_id": self.order_id,
            "gateway": self.gateway,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "last_error": self.last_error,
            "next_retry_at": self.next_retry_at.isoformat() if self.next_retry_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }


class WebhookStats(Base):
    """Агрегированная статистика webhook по дням."""
    __tablename__ = 'webhook_stats'
    __table_args__ = (
        Index('ix_stats_gateway_date', 'gateway', 'date', unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    gateway = Column(String, nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)  # Дата (без времени)
    
    # Счётчики
    total_received = Column(Integer, default=0)
    total_processed = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    total_retries = Column(Integer, default=0)
    
    # Временные метки
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<WebhookStats(gateway={self.gateway}, date={self.date}, processed={self.total_processed})>"
