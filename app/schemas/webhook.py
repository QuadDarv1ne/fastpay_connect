"""Webhook management schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class WebhookEventResponse(BaseModel):
    """Ответ с деталями webhook события."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    order_id: str
    gateway: str
    status: str
    retry_count: int
    max_retries: int
    last_error: Optional[str] = None
    next_retry_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    processed_at: Optional[str] = None


class WebhookEventListResponse(BaseModel):
    """Ответ со списком webhook событий."""
    events: List[WebhookEventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class WebhookStatsResponse(BaseModel):
    """Ответ со статистикой webhook."""
    total: int
    by_status: Dict[str, int]
    by_gateway: Dict[str, int]
    retrying: int
    failed: int
    period_days: int


class WebhookRetryRequest(BaseModel):
    """Запрос на повторную отправку webhook."""
    force: bool = Field(False, description="Принудительная отправка независимо от статуса")
