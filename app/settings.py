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
    json_logs: bool = False
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

    # Email уведомления
    mail_username: Optional[str] = None
    mail_password: Optional[str] = None
    mail_server: Optional[str] = None
    mail_port: int = 587
    mail_from_email: Optional[str] = None
    mail_enabled: bool = False


# Глобальный экземпляр настроек
settings = Settings()
