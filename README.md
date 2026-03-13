# 💳 FastPay Connect

![FastPay Connect](fastpay_connect.png)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-Custom%20with%20Restrictions-orange)](./LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/QuadDarv1ne/fastpay_connect?style=social)](https://github.com/QuadDarv1ne/fastpay_connect/stargazers)

**fastpay_connect** — это мощный и гибкий фреймворк для интеграции различных платёжных систем через FastAPI.

Проект предоставляет унифицированный интерфейс для работы с популярными платёжными шлюзами, упрощая процесс приёма онлайн-платежей в ваших приложениях.

---

## 📋 Содержание

- [Особенности](#-особенности)
- [Поддерживаемые платёжные системы](#-поддерживаемые-платёжные-системы)
- [Установка](#-установка)
- [Быстрый старт](#-быстрый-старт)
- [Конфигурация](#-конфигурация)
- [API Документация](#-api-документация)
- [Примеры использования](#-примеры-использования)
- [Структура проекта](#-структура-проекта)
- [Вклад в проект](#-вклад-в-проект)
- [Лицензия](#-лицензия)
- [Контакты](#-контакты)

---

## ✨ Особенности

- 🚀 **Высокая производительность** — построен на FastAPI с асинхронной обработкой запросов
- 🔌 **Модульная архитектура** — легко добавлять новые платёжные системы
- 🔐 **Безопасность** — встроенная валидация webhook-уведомлений и подписей
- 📝 **Автодокументация** — интерактивная Swagger UI документация из коробки
- 🧪 **Готов к тестированию** — поддержка тестовых режимов всех платёжных систем
- ⚙️ **Гибкая конфигурация** — настройка через переменные окружения или конфиг-файлы

---

## 💳 Поддерживаемые платёжные системы

| Платёжная система | Статус | Функционал |
|-------------------|--------|------------|
| **ЮKassa** (бывшая Яндекс.Касса) | ✅ Поддерживается | Оплата, возврат, webhook |
| **Tinkoff Касса** | ✅ Поддерживается | Оплата, возврат, webhook |
| **CloudPayments** | ✅ Поддерживается | Оплата, возврат, webhook |
| **UnitPay** | ✅ Поддерживается | Оплата, возврат, webhook |
| **Робокасса** | ✅ Поддерживается | Оплата, возврат, webhook |

---

## 📦 Установка

### Требования

- Python 3.10 или выше
- pip или poetry

### Клонирование репозитория

```bash
git clone https://github.com/QuadDarv1ne/fastpay_connect.git
cd fastpay_connect
```

### Установка зависимостей

С использованием pip:
```bash
pip install -r requirements.txt
```

С использованием poetry:
```bash
poetry install
```

---

## 🚀 Быстрый старт

### 1. Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
# ЮKassa
YOOKASSA_SHOP_ID=your_shop_id
YOOKASSA_SECRET_KEY=your_secret_key

# Tinkoff
TINKOFF_TERMINAL_KEY=your_terminal_key
TINKOFF_SECRET_KEY=your_secret_key

# CloudPayments
CLOUDPAYMENTS_PUBLIC_ID=your_public_id
CLOUDPAYMENTS_API_SECRET=your_api_secret

# UnitPay
UNITPAY_SECRET_KEY=your_secret_key

# Робокасса
ROBOKASSA_MERCHANT_LOGIN=your_login
ROBOKASSA_PASSWORD1=your_password1
ROBOKASSA_PASSWORD2=your_password2
```

### 2. Запуск сервера

```bash
# С использованием uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Или напрямую через Python
python main.py
```

### 3. Проверка работоспособности

Откройте браузер и перейдите по адресу:
- API документация: `http://localhost:8000/docs`
- Альтернативная документация: `http://localhost:8000/redoc`

---

## ⚙️ Конфигурация

### Переменные окружения

| Переменная | Описание | Обязательно |
|------------|----------|-------------|
| `YOOKASSA_SHOP_ID` | Идентификатор магазина в ЮKassa | Да (для ЮKassa) |
| `YOOKASSA_SECRET_KEY` | Секретный ключ ЮKassa | Да (для ЮKassa) |
| `TINKOFF_TERMINAL_KEY` | Ключ терминала Tinkoff | Да (для Tinkoff) |
| `TINKOFF_SECRET_KEY` | Секретный ключ Tinkoff | Да (для Tinkoff) |
| `CLOUDPAYMENTS_PUBLIC_ID` | Публичный ID CloudPayments | Да (для CP) |
| `CLOUDPAYMENTS_API_SECRET` | API секрет CloudPayments | Да (для CP) |
| `UNITPAY_SECRET_KEY` | Секретный ключ UnitPay | Да (для UnitPay) |
| `ROBOKASSA_MERCHANT_LOGIN` | Логин мерчанта Робокасса | Да (для Робокасса) |
| `ROBOKASSA_PASSWORD1` | Пароль 1 Робокасса | Да (для Робокасса) |
| `ROBOKASSA_PASSWORD2` | Пароль 2 Робокасса | Да (для Робокасса) |

### Тестовый режим

Все платёжные системы поддерживают тестовый режим для разработки и отладки. Настройте соответствующие параметры в конфигурации каждой системы.

---

## 📖 API Документация

После запуска сервера доступна интерактивная документация:

- **Swagger UI**: `/docs` — интерактивное тестирование API
- **ReDoc**: `/redoc` — красивая документация для чтения
- **OpenAPI JSON**: `/openapi.json` — спецификация OpenAPI

---

## 💡 Примеры использования

### Создание платежа через ЮKassa

```python
import httpx

async def create_payment():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/yookassa/create-payment",
            json={
                "amount": 1000.00,
                "currency": "RUB",
                "description": "Оплата заказа #12345",
                "return_url": "https://example.com/success"
            }
        )
        return response.json()
```

### Обработка webhook

```python
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook/yookassa")
async def yookassa_webhook(request: Request):
    payload = await request.json()
    # Обработка уведомления о платеже
    event = payload.get("event")
    payment = payload.get("object")
    
    if event == "payment.succeeded":
        # Логика успешной оплаты
        pass
    
    return {"status": "ok"}
```

---

## 📁 Структура проекта

```
fastpay_connect/
├── main.py                 # Точка входа FastAPI приложения
├── config.py               # Конфигурация проекта
├── requirements.txt        # Зависимости проекта
├── .env.example            # Пример переменных окружения
├── LICENSE                 # Лицензия (английский)
├── LICENSE_RU              # Лицензия (русский)
├── README.md               # Документация
│
├── api/                    # API маршруты
│   ├── __init__.py
│   ├── yookassa.py         # Эндпоинты ЮKassa
│   ├── tinkoff.py          # Эндпоинты Tinkoff
│   ├── cloudpayments.py    # Эндпоинты CloudPayments
│   ├── unitpay.py          # Эндпоинты UnitPay
│   └── robokassa.py        # Эндпоинты Робокасса
│
├── services/               # Бизнес-логика
│   ├── __init__.py
│   ├── base.py             # Базовый класс платёжного сервиса
│   ├── yookassa_service.py
│   ├── tinkoff_service.py
│   ├── cloudpayments_service.py
│   ├── unitpay_service.py
│   └── robokassa_service.py
│
├── models/                 # Pydantic модели
│   ├── __init__.py
│   ├── payment.py          # Модели платежей
│   └── webhook.py          # Модели webhook
│
└── utils/                  # Вспомогательные функции
    ├── __init__.py
    ├── security.py         # Валидация подписей
    └── helpers.py          # Вспомогательные функции
```

---

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта! Перед тем как внести изменения:

1. **Уведомите автора** о намерении использовать или модифицировать код через [GitHub Issues](https://github.com/QuadDarv1ne/fastpay_connect/issues)
2. Сделайте fork репозитория
3. Создайте ветку для ваших изменений (`git checkout -b feature/amazing-feature`)
4. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
5. Отправьте изменения в ваш fork (`git push origin feature/amazing-feature`)
6. Создайте Pull Request

Пожалуйста, убедитесь, что ваш код следует стилю проекта и включает соответствующие тесты.

---

## 📄 Лицензия

Этот проект распространяется под специальной лицензией с ограничениями.

### Что разрешено ✅

- Бесплатное использование в некоммерческих проектах
- Модификация и создание производных работ с сохранением авторства
- Распространение под этой же лицензией (ShareAlike)

### Что запрещено ❌

- Коммерческое использование без письменного согласия автора
- Удаление или изменение уведомлений об авторских правах
- Наложение дополнительных ограничений на получателей

### Обязательные требования 📋

- Указание имени автора: **Dupley Maxim Igorevich (QuadDarv1ne)**
- Ссылка на оригинальный репозиторий
- **Уведомление автора** перед любым использованием

Для коммерческого использования свяжитесь с автором.

📄 [Полный текст лицензии (English)](./LICENSE) | [Полный текст лицензии (Русский)](./LICENSE_RU)

---

## 📞 Контакты

**Автор:** Дуплей Максим Игоревич (QuadDarv1ne)

- 💻 GitHub: [QuadDarv1ne](https://github.com/QuadDarv1ne)
- 📬 Issues: [fastpay_connect/issues](https://github.com/QuadDarv1ne/fastpay_connect/issues)
- 📁 Репозиторий: [fastpay_connect](https://github.com/QuadDarv1ne/fastpay_connect)

---

<p align="center">
  <strong>⭐ Если проект был полезен, поставьте звёздочку</strong>
</p>

<p align="center">
  Сделано с ❤️ для разработчиков
</p>
