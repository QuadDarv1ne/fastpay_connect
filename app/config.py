import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


def _parse_list(env_var: str, default: str) -> List[str]:
    """Parse comma-separated env var to list."""
    value = os.getenv(env_var, default)
    return [item.strip() for item in value.split(",") if item.strip()]


YOOKASSA_API_KEY = os.getenv("YOOKASSA_API_KEY")
TINKOFF_API_KEY = os.getenv("TINKOFF_API_KEY")
CLOUDPAYMENTS_API_KEY = os.getenv("CLOUDPAYMENTS_API_KEY")
UNITPAY_API_KEY = os.getenv("UNITPAY_API_KEY")
ROBOKASSA_API_KEY = os.getenv("ROBOKASSA_API_KEY")

YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
TINKOFF_SECRET_KEY = os.getenv("TINKOFF_SECRET_KEY")
CLOUDPAYMENTS_SECRET_KEY = os.getenv("CLOUDPAYMENTS_SECRET_KEY")
UNITPAY_SECRET_KEY = os.getenv("UNITPAY_SECRET_KEY")
ROBOKASSA_SECRET_KEY = os.getenv("ROBOKASSA_SECRET_KEY")

YOOKASSA_RETURN_URL = os.getenv("YOOKASSA_RETURN_URL", "https://localhost:8080/payment/return")
TINKOFF_RETURN_URL = os.getenv("TINKOFF_RETURN_URL", "https://localhost:8080/payment/return")
CLOUDPAYMENTS_RETURN_URL = os.getenv("CLOUDPAYMENTS_RETURN_URL", "https://localhost:8080/payment/return")
UNITPAY_RETURN_URL = os.getenv("UNITPAY_RETURN_URL", "https://localhost:8080/payment/return")
ROBOKASSA_RETURN_URL = os.getenv("ROBOKASSA_RETURN_URL", "https://localhost:8080/payment/return")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fastpay_connect.db")
SECRET_KEY = os.getenv("SECRET_KEY")
ALLOWED_HOSTS = _parse_list("ALLOWED_HOSTS", "localhost")
ALLOWED_ORIGINS = _parse_list("ALLOWED_ORIGINS", "http://localhost,https://localhost")

YOOKASSA_IPS = _parse_list("YOOKASSA_IPS", "77.75.153.0/24,77.75.156.0/24,77.75.157.0/24,77.75.158.0/24")
TINKOFF_IPS = _parse_list("TINKOFF_IPS", "185.215.82.0/24")
CLOUDPAYMENTS_IPS = _parse_list("CLOUDPAYMENTS_IPS", "95.163.0.0/16")
UNITPAY_IPS = _parse_list("UNITPAY_IPS", "109.207.0.0/16")
ROBOKASSA_IPS = _parse_list("ROBOKASSA_IPS", "31.131.248.0/24")

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
