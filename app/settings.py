"""Настройки приложения с использованием Pydantic Settings."""

from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Общие настройки
    debug: bool = False
    log_level: str = "INFO"
    secret_key: Optional[str] = None
    database_url: str = "sqlite+aiosqlite:///./fastpay_connect.db"
    allowed_hosts: List[str] = Field(default_factory=lambda: ["localhost"])
    allowed_origins: List[str] = Field(default_factory=lambda: ["http://localhost"])

    # YooKassa
    yookassa_api_key: Optional[str] = None
    yookassa_secret_key: Optional[str] = None
    yookassa_return_url: str = "https://localhost:8080/payment/return"
    yookassa_ips: List[str] = Field(
        default_factory=lambda: [
            "77.75.153.0/24",
            "77.75.156.0/24",
            "77.75.157.0/24",
            "77.75.158.0/24",
        ]
    )

    # Tinkoff
    tinkoff_api_key: Optional[str] = None
    tinkoff_secret_key: Optional[str] = None
    tinkoff_return_url: str = "https://localhost:8080/payment/return"
    tinkoff_ips: List[str] = Field(default_factory=lambda: ["185.215.82.0/24"])

    # CloudPayments
    cloudpayments_api_key: Optional[str] = None
    cloudpayments_secret_key: Optional[str] = None
    cloudpayments_return_url: str = "https://localhost:8080/payment/return"
    cloudpayments_ips: List[str] = Field(
        default_factory=lambda: ["95.163.0.0/16"]
    )

    # UnitPay
    unitpay_api_key: Optional[str] = None
    unitpay_secret_key: Optional[str] = None
    unitpay_return_url: str = "https://localhost:8080/payment/return"
    unitpay_ips: List[str] = Field(
        default_factory=lambda: ["109.207.0.0/16"]
    )

    # Robokassa
    robokassa_api_key: Optional[str] = None
    robokassa_secret_key: Optional[str] = None
    robokassa_return_url: str = "https://localhost:8080/payment/return"
    robokassa_ips: List[str] = Field(
        default_factory=lambda: ["31.131.248.0/24"]
    )

    # Mail (опционально)
    mail_username: Optional[str] = None
    mail_password: Optional[str] = None
    mail_server: Optional[str] = None
    mail_port: int = 587


# Глобальный экземпляр настроек
settings = Settings()


# Прокси-атрибуты для обратной совместимости с config.py
def __getattr__(name: str):
    """Обратная совместимость с old config."""
    mapping = {
        "YOOKASSA_API_KEY": "yookassa_api_key",
        "YOOKASSA_SECRET_KEY": "yookassa_secret_key",
        "YOOKASSA_RETURN_URL": "yookassa_return_url",
        "YOOKASSA_IPS": "yookassa_ips",
        "TINKOFF_API_KEY": "tinkoff_api_key",
        "TINKOFF_SECRET_KEY": "tinkoff_secret_key",
        "TINKOFF_RETURN_URL": "tinkoff_return_url",
        "TINKOFF_IPS": "tinkoff_ips",
        "CLOUDPAYMENTS_API_KEY": "cloudpayments_api_key",
        "CLOUDPAYMENTS_SECRET_KEY": "cloudpayments_secret_key",
        "CLOUDPAYMENTS_RETURN_URL": "cloudpayments_return_url",
        "CLOUDPAYMENTS_IPS": "cloudpayments_ips",
        "UNITPAY_API_KEY": "unitpay_api_key",
        "UNITPAY_SECRET_KEY": "unitpay_secret_key",
        "UNITPAY_RETURN_URL": "unitpay_return_url",
        "UNITPAY_IPS": "unitpay_ips",
        "ROBOKASSA_API_KEY": "robokassa_api_key",
        "ROBOKASSA_SECRET_KEY": "robokassa_secret_key",
        "ROBOKASSA_RETURN_URL": "robokassa_return_url",
        "ROBOKASSA_IPS": "robokassa_ips",
        "SECRET_KEY": "secret_key",
        "DATABASE_URL": "database_url",
        "ALLOWED_HOSTS": "allowed_hosts",
        "ALLOWED_ORIGINS": "allowed_origins",
        "DEBUG": "debug",
        "LOG_LEVEL": "log_level",
        "MAIL_USERNAME": "mail_username",
        "MAIL_PASSWORD": "mail_password",
        "MAIL_SERVER": "mail_server",
        "MAIL_PORT": "mail_port",
    }

    if name in mapping:
        return getattr(settings, mapping[name])

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """Для обратной совместимости."""
    old_config_vars = [
        "YOOKASSA_API_KEY", "YOOKASSA_SECRET_KEY", "YOOKASSA_RETURN_URL", "YOOKASSA_IPS",
        "TINKOFF_API_KEY", "TINKOFF_SECRET_KEY", "TINKOFF_RETURN_URL", "TINKOFF_IPS",
        "CLOUDPAYMENTS_API_KEY", "CLOUDPAYMENTS_SECRET_KEY", "CLOUDPAYMENTS_RETURN_URL", "CLOUDPAYMENTS_IPS",
        "UNITPAY_API_KEY", "UNITPAY_SECRET_KEY", "UNITPAY_RETURN_URL", "UNITPAY_IPS",
        "ROBOKASSA_API_KEY", "ROBOKASSA_SECRET_KEY", "ROBOKASSA_RETURN_URL", "ROBOKASSA_IPS",
        "SECRET_KEY", "DATABASE_URL", "ALLOWED_HOSTS", "ALLOWED_ORIGINS", "DEBUG", "LOG_LEVEL",
        "MAIL_USERNAME", "MAIL_PASSWORD", "MAIL_SERVER", "MAIL_PORT",
    ]
    return old_config_vars + ["settings", "Settings"]
