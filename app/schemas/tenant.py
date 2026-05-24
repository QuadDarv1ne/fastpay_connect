"""
Schemas for tenant management.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TenantBase(BaseModel):
    """Базовая схема tenant."""

    name: str = Field(..., min_length=1, max_length=100, description="Название организации")
    slug: str = Field(..., min_length=3, max_length=50, pattern=r'^[a-z0-9-]+$', description="URL-friendly идентификатор")
    description: Optional[str] = Field(None, max_length=1000, description="Описание")
    contact_email: Optional[str] = Field(None, max_length=255, description="Email для связи")
    contact_phone: Optional[str] = Field(None, max_length=20, description="Телефон для связи")


class TenantCreate(TenantBase):
    """Схема для создания tenant."""

    allowed_payment_gateways: Optional[List[str]] = Field(
        None,
        description="Список разрешённых платёжных шлюзов"
    )


class TenantUpdate(BaseModel):
    """Схема для обновления tenant."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    slug: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r'^[a-z0-9-]+$')
    description: Optional[str] = Field(None, max_length=1000)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=20)
    status: Optional[str] = Field(None, description="Статус tenant")
    allowed_payment_gateways: Optional[List[str]] = None
    settings: Optional[Dict[str, Any]] = None


class TenantResponse(TenantBase):
    """Схема ответа tenant."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    api_key: str
    status: str
    allowed_payment_gateways: Optional[List[str]] = None
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
