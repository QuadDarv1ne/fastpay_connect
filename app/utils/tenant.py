"""
Tenant context utilities for multi-tenant support.
"""

from contextvars import ContextVar
from typing import Optional

from app.models.tenant import Tenant

# Context variable для хранения текущего tenant в запросе
tenant_context: ContextVar[Optional[Tenant]] = ContextVar("tenant_context", default=None)


def get_current_tenant() -> Optional[Tenant]:
    """Получить текущий tenant из контекста."""
    return tenant_context.get()


def set_current_tenant(tenant: Optional[Tenant]) -> None:
    """Установить текущий tenant в контексте."""
    tenant_context.set(tenant)


def reset_tenant_context() -> None:
    """Сбросить контекст tenant."""
    set_current_tenant(None)
