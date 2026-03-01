import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Получаем переменные окружения
YOOKASSA_API_KEY = os.getenv("YOOKASSA_API_KEY")
TINKOFF_API_KEY = os.getenv("TINKOFF_API_KEY")
CLOUDPAYMENTS_API_KEY = os.getenv("CLOUDPAYMENTS_API_KEY")
UNITPAY_API_KEY = os.getenv("UNITPAY_API_KEY")
ROBOKASSA_API_KEY = os.getenv("ROBOKASSA_API_KEY")

# Секретные ключи для подписи
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
TINKOFF_SECRET_KEY = os.getenv("TINKOFF_SECRET_KEY")
CLOUDPAYMENTS_SECRET_KEY = os.getenv("CLOUDPAYMENTS_SECRET_KEY")
UNITPAY_SECRET_KEY = os.getenv("UNITPAY_SECRET_KEY")
ROBOKASSA_SECRET_KEY = os.getenv("ROBOKASSA_SECRET_KEY")

# URL возврата после оплаты
YOOKASSA_RETURN_URL = os.getenv("YOOKASSA_RETURN_URL", "https://localhost:8080/payment/return")
TINKOFF_RETURN_URL = os.getenv("TINKOFF_RETURN_URL", "https://localhost:8080/payment/return")
CLOUDPAYMENTS_RETURN_URL = os.getenv("CLOUDPAYMENTS_RETURN_URL", "https://localhost:8080/payment/return")
UNITPAY_RETURN_URL = os.getenv("UNITPAY_RETURN_URL", "https://localhost:8080/payment/return")
ROBOKASSA_RETURN_URL = os.getenv("ROBOKASSA_RETURN_URL", "https://localhost:8080/payment/return")

# Для базы данных и секретного ключа
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fastpay_connect.db")
SECRET_KEY = os.getenv("SECRET_KEY")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost").split(",")  # Если несколько хостов

# IP-адреса платёжных систем для webhook (белый список)
YOOKASSA_IPS = os.getenv("YOOKASSA_IPS", "77.75.153.0/24,77.75.156.0/24,77.75.157.0/24,77.75.158.0/24").split(",")
TINKOFF_IPS = os.getenv("TINKOFF_IPS", "185.215.82.0/24").split(",")
CLOUDPAYMENTS_IPS = os.getenv("CLOUDPAYMENTS_IPS", "95.163.0.0/16").split(",")
UNITPAY_IPS = os.getenv("UNITPAY_IPS", "109.207.0.0/16").split(",")
ROBOKASSA_IPS = os.getenv("ROBOKASSA_IPS", "31.131.248.0/24").split(",")

# Для отладки
DEBUG = os.getenv("DEBUG", "True") == "True"  # Преобразуем строку в булево значение

# Для почтовых настроек
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))  # По умолчанию 587
