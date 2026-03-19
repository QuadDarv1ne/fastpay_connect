"""
Tenant model for multi-tenant support.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime, timezone
from typing import Optional, List
from app.database import Base
import enum


class TenantStatus(enum.Enum):
    """Статусы tenant."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class Tenant(Base):
    """Модель организации (tenant) для multi-tenant архитектуры.

    Каждый tenant изолирован:
    - Свои пользователи
    - Свои платежи
    - Свои webhook события
    """

    __tablename__ = 'tenants'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    slug = Column(String(50), unique=True, index=True, nullable=False)
    api_key = Column(String(64), unique=True, index=True, nullable=False)
    status = Column(String(20), default=TenantStatus.ACTIVE.value, index=True)
    
    # Информация о компании
    description = Column(Text, nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    
    # Настройки
    settings_json = Column(String(4096), nullable=True)  # JSON настройки tenant
    allowed_payment_gateways = Column(String(255), nullable=True)  # JSON список шлюзов
    
    # Метаданные
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )
    
    def __repr__(self) -> str:
        return f"<Tenant(name={self.name}, slug={self.slug})>"

    def get_settings(self) -> dict:
        """Получить настройки tenant."""
        import json
        if not self.settings_json:
            return {}
        try:
            return json.loads(self.settings_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    def get_allowed_gateways(self) -> List[str]:
        """Получить разрешённые платёжные шлюзы."""
        import json
        if not self.allowed_payment_gateways:
            return []
        try:
            return json.loads(self.allowed_payment_gateways)
        except (json.JSONDecodeError, TypeError):
            return []

    def is_gateway_allowed(self, gateway: str) -> bool:
        """Проверить, разрешён ли платёжный шлюз."""
        allowed = self.get_allowed_gateways()
        return not allowed or gateway in allowed
