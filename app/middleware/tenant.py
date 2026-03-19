"""
Tenant middleware for multi-tenant isolation.

Извлекает tenant из API ключа и устанавливает в контекст запроса.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Optional
import logging

from app.database import SessionLocal
from app.models.tenant import Tenant
from app.utils.tenant import set_current_tenant, reset_tenant_context

logger = logging.getLogger(__name__)


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware для определения tenant из API ключа.

    API ключ передаётся в заголовке: X-API-Key
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Пропускаем health check и документацию
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Извлекаем API ключ из заголовка
        api_key = request.headers.get("X-API-Key")

        if api_key:
            tenant = await self._get_tenant_by_api_key(api_key)
            if tenant:
                if tenant.status != "active":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Tenant account is {tenant.status}",
                    )
                set_current_tenant(tenant)
                request.state.tenant = tenant
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key",
                    headers={"WWW-Authenticate": "API-Key"},
                )
        else:
            # Если API ключ не предоставлен, tenant не установлен
            # Это позволяет работать endpoints без tenant (например, регистрация)
            reset_tenant_context()
            request.state.tenant = None

        try:
            response = await call_next(request)
            return response
        finally:
            # Сбрасываем контекст после запроса
            reset_tenant_context()

    async def _get_tenant_by_api_key(self, api_key: str) -> Optional[Tenant]:
        """Получить tenant по API ключу."""
        db = SessionLocal()
        try:
            tenant = db.query(Tenant).filter(Tenant.api_key == api_key).first()
            return tenant
        finally:
            db.close()
