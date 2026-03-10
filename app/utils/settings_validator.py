import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class SettingsValidator:
    """Валидация настроек приложения."""

    def __init__(self):
        self.errors: List[str] = []

    def check_required(self, value: Optional[str], name: str) -> bool:
        """Проверка обязательного параметра."""
        if not value:
            self.errors.append(f"Required setting '{name}' is not configured")
            return False
        return True

    def validate_payment_gateway(
        self, name: str, api_key: Optional[str], secret_key: Optional[str]
    ) -> bool:
        """Проверка настроек платёжного шлюза."""
        ok = True
        if not api_key:
            self.errors.append(f"{name}: API key not configured")
            ok = False
        if not secret_key:
            self.errors.append(f"{name}: Secret key not configured")
            ok = False
        return ok

    def validate_all(
        self,
        yookassa_key: Optional[str],
        yookassa_secret: Optional[str],
        tinkoff_key: Optional[str],
        tinkoff_secret: Optional[str],
        cloudpayments_key: Optional[str],
        cloudpayments_secret: Optional[str],
        unitpay_key: Optional[str],
        unitpay_secret: Optional[str],
        robokassa_key: Optional[str],
        robokassa_secret: Optional[str],
        secret_key: Optional[str],
        database_url: Optional[str],
    ) -> bool:
        """Полная валидация всех настроек."""
        self.errors = []

        self.check_required(secret_key, "SECRET_KEY")
        self.check_required(database_url, "DATABASE_URL")

        # Логируем предупреждения для платёжных шлюзов (не блокируем запуск)
        if not yookassa_key:
            logger.warning("YooKassa: API key not configured")
        if not tinkoff_key:
            logger.warning("Tinkoff: API key not configured")
        if not cloudpayments_key:
            logger.warning("CloudPayments: API key not configured")
        if not unitpay_key:
            logger.warning("UnitPay: API key not configured")
        if not robokassa_key:
            logger.warning("Robokassa: API key not configured")

        if self.errors:
            for error in self.errors:
                logger.error(f"Configuration error: {error}")
            return False

        logger.info("All configuration settings validated successfully")
        return True


settings_validator = SettingsValidator()
