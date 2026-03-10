"""Исключения платёжных шлюзов."""

from typing import Any, Dict, Optional


class PaymentGatewayError(Exception):
    """Базовое исключение для платёжных шлюзов."""

    def __init__(
        self,
        message: str = "Payment gateway error",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class PaymentGatewayConfigError(PaymentGatewayError):
    """Ошибка конфигурации платёжного шлюза."""

    def __init__(self, message: str = "Payment gateway not configured"):
        super().__init__(message=message, status_code=500)


class PaymentGatewayConnectionError(PaymentGatewayError):
    """Ошибка соединения с платёжным шлюзом."""

    def __init__(self, message: str = "Failed to connect to payment gateway"):
        super().__init__(message=message, status_code=503)


class PaymentGatewayTimeoutError(PaymentGatewayError):
    """Таймаут запроса к платёжному шлюзу."""

    def __init__(self, message: str = "Payment gateway request timeout"):
        super().__init__(message=message, status_code=504)


class PaymentGatewayAPIError(PaymentGatewayError):
    """Ошибка API платёжного шлюза."""

    def __init__(
        self,
        message: str = "Payment gateway API error",
        status_code: int = 400,
        response_body: Optional[Dict[str, Any]] = None,
    ):
        details = {"response_body": response_body} if response_body else {}
        super().__init__(message=message, status_code=status_code, details=details)
