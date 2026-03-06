"""Исключения для платёжных шлюзов."""

from typing import Any, Dict, Optional


class PaymentGatewayError(Exception):
    """Базовое исключение для платёжных шлюзов."""

    def __init__(
        self,
        message: str = "Payment gateway error",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Конвертация в словарь для API ответа."""
        return {"error": self.message, "details": self.details}


class PaymentGatewayConfigError(PaymentGatewayError):
    """Ошибка конфигурации платёжного шлюза."""

    def __init__(self, message: str = "Payment gateway not configured"):
        super().__init__(message=message)


class PaymentGatewayAPIError(PaymentGatewayError):
    """Ошибка API платёжной системы."""

    def __init__(
        self,
        message: str = "Payment gateway API error",
        status_code: Optional[int] = None,
        response_body: Optional[Dict[str, Any]] = None,
    ):
        self.status_code = status_code
        self.response_body = response_body or {}
        details = {
            "status_code": status_code,
            "response": self.response_body,
        }
        super().__init__(message=message, details=details)


class PaymentGatewayTimeoutError(PaymentGatewayError):
    """Таймаут запроса к платёжному шлюзу."""

    def __init__(self, message: str = "Payment gateway timeout"):
        super().__init__(message=message)


class PaymentGatewayConnectionError(PaymentGatewayError):
    """Ошибка соединения с платёжным шлюзом."""

    def __init__(self, message: str = "Payment gateway connection error"):
        super().__init__(message=message)
