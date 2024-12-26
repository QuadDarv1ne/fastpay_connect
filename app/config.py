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

# Для базы данных и секретного ключа
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS").split(",")  # Если несколько хостов

# Для отладки
DEBUG = os.getenv("DEBUG", "True") == "True"  # Преобразуем строку в булево значение

# Для почтовых настроек
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_SERVER = os.getenv("MAIL_SERVER")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))  # По умолчанию 587
