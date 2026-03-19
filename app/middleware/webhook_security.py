"""Middleware для безопасности webhook уведомлений.

Автоматическая проверка IP адресов и подписей webhook уведомлений
от платёжных шлюзов.
"""

import logging
from typing import Callable, Dict, List, Optional
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.utils.ip_validator import is_ip_in_whitelist
from app.settings import settings

logger = logging.getLogger(__name__)


class WebhookSecurityMiddleware(BaseHTTPMiddleware):
    """Middleware для проверки безопасности webhook.

    Проверяет:
    - IP адрес отправителя (если настроен whitelist)
    - Обязательные заголовки безопасности
    - Метод HTTP (только POST для webhook)

    Пример использования:
        app.add_middleware(WebhookSecurityMiddleware)
    """

    # Whitelist IP для каждого платёжного шлюза
    GATEWAY_IP_WHITELISTS: Dict[str, List[str]] = {
        "yookassa": settings.yookassa_ips,
        "tinkoff": settings.tinkoff_ips,
        "cloudpayments": settings.cloudpayments_ips,
        "unitpay": settings.unitpay_ips,
        "robokassa": settings.robokassa_ips,
        "rustore": settings.rustore_ips,
        "sbp": settings.sbp_ips,
    }

    # Обязательные заголовки для каждого шлюза
    GATEWAY_REQUIRED_HEADERS: Dict[str, List[str]] = {
        "yookassa": [],  # YooKassa не требует специальных заголовков
        "tinkoff": [],  # Tinkoff не требует специальных заголовков
        "cloudpayments": [],  # CloudPayments не требует специальных заголовков
        "unitpay": [],  # UnitPay не требует специальных заголовков
        "robokassa": [],  # RoboKassa не требует специальных заголовков
        "rustore": ["X-Signature"],  # RuStore требует подпись
        "sbp": ["X-Signature", "X-Timestamp"],  # SBP требует подпись и timestamp
    }

    def __init__(self, app: ASGIApp) -> None:
        """Инициализация middleware."""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Request:
        """Обработка запроса.

        Args:
            request: HTTP запрос
            call_next: Следующий middleware/handler

        Returns:
            Response от следующего middleware
        """
        # Проверяем только webhook пути
        if not self._is_webhook_path(request.url.path):
            return await call_next(request)

        # Определяем шлюз из пути
        gateway_name = self._extract_gateway_name(request.url.path)

        if gateway_name:
            # Проверяем IP адрес
            await self._verify_ip(request, gateway_name)

            # Проверяем обязательные заголовки
            self._verify_required_headers(request, gateway_name)

            # Проверяем метод HTTP
            self._verify_http_method(request)

        return await call_next(request)

    def _is_webhook_path(self, path: str) -> bool:
        """Проверка что путь является webhook endpoint."""
        return "/webhook" in path.lower() or "/webhooks" in path.lower()

    def _extract_gateway_name(self, path: str) -> Optional[str]:
        """Извлечение имени шлюза из пути.

        Примеры:
            /api/v1/webhooks/rustore -> rustore
            /api/v1/webhooks/sbp -> sbp
            /api/v1/rustore/webhook -> rustore
        """
        path_lower = path.lower()

        for gateway_name in self.GATEWAY_IP_WHITELISTS.keys():
            if gateway_name in path_lower:
                return gateway_name

        return None

    async def _verify_ip(self, request: Request, gateway_name: str) -> None:
        """Проверка IP адреса запроса.

        Args:
            request: HTTP запрос
            gateway_name: Имя платёжного шлюза

        Raises:
            HTTPException: Если IP не в whitelist
        """
        whitelist = self.GATEWAY_IP_WHITELISTS.get(gateway_name, [])

        if not whitelist:
            logger.debug(f"Webhook IP whitelist not configured for {gateway_name}")
            return

        client_ip: Optional[str] = request.client.host if request.client else None

        if not client_ip:
            logger.warning(f"Webhook from {gateway_name}: cannot determine client IP")
            return

        # Локальные адреса пропускаем
        if client_ip in ("127.0.0.1", "localhost", "::1"):
            return

        if not is_ip_in_whitelist(client_ip, whitelist):
            logger.warning(
                f"Webhook access denied from IP {client_ip} for {gateway_name}. "
                f"Allowed: {whitelist}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: IP {client_ip} not in whitelist for {gateway_name}",
            )

        logger.debug(f"Webhook IP {client_ip} verified for {gateway_name}")

    def _verify_required_headers(
        self, request: Request, gateway_name: str
    ) -> None:
        """Проверка обязательных заголовков.

        Args:
            request: HTTP запрос
            gateway_name: Имя платёжного шлюза

        Raises:
            HTTPException: Если обязательные заголовки отсутствуют
        """
        required_headers = self.GATEWAY_REQUIRED_HEADERS.get(gateway_name, [])

        for header in required_headers:
            if header not in request.headers:
                logger.warning(
                    f"Webhook from {gateway_name} missing required header: {header}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing required header: {header}",
                )

        logger.debug(f"All required headers present for {gateway_name}")

    def _verify_http_method(self, request: Request) -> None:
        """Проверка метода HTTP (только POST для webhook).

        Args:
            request: HTTP запрос

        Raises:
            HTTPException: Если метод не POST
        """
        if request.method != "POST":
            logger.warning(f"Webhook received with non-POST method: {request.method}")
            raise HTTPException(
                status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
                detail="Method not allowed. Webhooks only accept POST.",
            )


def setup_webhook_security_middleware(app: FastAPI) -> None:
    """Настройка middleware безопасности webhook.

    Args:
        app: FastAPI приложение
    """
    app.add_middleware(WebhookSecurityMiddleware)
    logger.info("Webhook security middleware enabled")


# Декоратор для защиты отдельных endpoints
def webhook_security_guard(
    gateway_name: str,
    require_signature: bool = True,
    require_timestamp: bool = False,
):
    """Декоратор для защиты webhook endpoints.

    Используется как альтернатива middleware для отдельных endpoints.

    Args:
        gateway_name: Имя платёжного шлюза
        require_signature: Требовать заголовок подписи
        require_timestamp: Требовать заголовок timestamp

    Example:
        @router.post("/rustore")
        @webhook_security_guard("rustore", require_signature=True)
        async def rustore_webhook(request: Request):
            ...
    """

    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            # Проверяем IP
            whitelist = WebhookSecurityMiddleware.GATEWAY_IP_WHITELISTS.get(
                gateway_name, []
            )
            if whitelist:
                client_ip = request.client.host if request.client else None
                if client_ip and client_ip not in ("127.0.0.1", "localhost", "::1"):
                    if not is_ip_in_whitelist(client_ip, whitelist):
                        raise HTTPException(
                            status_code=403,
                            detail=f"IP {client_ip} not allowed",
                        )

            # Проверяем заголовки
            if require_signature and "X-Signature" not in request.headers:
                raise HTTPException(
                    status_code=400,
                    detail="Missing required header: X-Signature",
                )

            if require_timestamp and "X-Timestamp" not in request.headers:
                raise HTTPException(
                    status_code=400,
                    detail="Missing required header: X-Timestamp",
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
