"""
API Versioning Middleware.

Supports API versioning through:
1. URL path prefix (/api/v1/, /api/v2/)
2. Custom header (X-API-Version: v1, v2)
3. Accept header (application/json; version=v1)
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class APIVersionMiddleware(BaseHTTPMiddleware):
    """Middleware для обработки версионирования API."""

    async def dispatch(self, request: Request, call_next):
        # Получаем версию из различных источников
        version_from_header = self._get_version_from_header(request)
        version_from_path = self._get_version_from_path(request.url.path)
        version_from_accept = self._get_version_from_accept_header(request)

        # Используем приоритет: path > header > accept
        api_version = version_from_path or version_from_header or version_from_accept

        if api_version:
            # Добавляем версию в request state для использования в handlers
            request.state.api_version = api_version
            
            # Логирование для отладки
            logger.debug(f"API version detected: {api_version} for path: {request.url.path}")

        response = await call_next(request)
        
        # Добавляем заголовок с версией в ответ
        if api_version:
            response.headers["X-API-Version"] = api_version
        
        return response

    def _get_version_from_header(self, request: Request) -> Optional[str]:
        """Получить версию из заголовка X-API-Version."""
        version = request.headers.get("X-API-Version", "").lower()
        if version in ["v1", "v2", "1", "2"]:
            return f"v{version[-1]}"
        return None

    def _get_version_from_path(self, path: str) -> Optional[str]:
        """Получить версию из пути URL."""
        if path.startswith("/api/v1/"):
            return "v1"
        elif path.startswith("/api/v2/"):
            return "v2"
        return None

    def _get_version_from_accept_header(self, request: Request) -> Optional[str]:
        """Получить версию из Accept header."""
        accept = request.headers.get("Accept", "")
        
        # Проверка на versioned accept header
        # Например: application/json; version=v1
        if "version=v1" in accept or "version=1" in accept:
            return "v1"
        elif "version=v2" in accept or "version=2" in accept:
            return "v2"
        
        # Проверка на media type versioning
        # Например: application/vnd.fastpay.v1+json
        if "vnd.fastpay.v1" in accept:
            return "v1"
        elif "vnd.fastpay.v2" in accept:
            return "v2"
        
        return None


class RequireAPIVersionMiddleware(BaseHTTPMiddleware):
    """
    Middleware для принудительного требования версии API.
    
    Может быть использован для deprecated endpoints или для требования
    явного указания версии API.
    """

    def __init__(self, app, required: bool = False, allowed_versions: Optional[list] = None):
        super().__init__(app)
        self.required = required
        self.allowed_versions = allowed_versions or ["v1", "v2"]

    async def dispatch(self, request: Request, call_next):
        # Пропускаем health check и документацию
        if request.url.path in ["/health", "/ready", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        api_version = getattr(request.state, "api_version", None)

        if self.required and not api_version:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "API version required",
                    "message": "Please specify API version via X-API-Version header or URL path",
                    "examples": {
                        "header": "X-API-Version: v1",
                        "path": "/api/v1/payments/create",
                        "accept": "Accept: application/json; version=v1",
                    }
                }
            )

        if api_version and api_version not in self.allowed_versions:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": "Unsupported API version",
                    "message": f"Version '{api_version}' is not supported",
                    "allowed_versions": self.allowed_versions,
                }
            )

        return await call_next(request)
