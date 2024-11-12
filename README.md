# fastpay_connect

![fastpay_connect](fastpay_connect.png)

**fastpay_connect** — это проект для демонстрации интеграции различных платёжных систем через `FastAPI`

**В проекте реализованы интеграции с популярными платёжными шлюзами, такими как:**

- `ЮKassa (бывшая Яндекс.Касса)`
- `Tinkoff Касса`
- `CloudPayments`
- `UnitPay`
- `Робокасса`

Проект служит в качестве учебного материала и примера того, как можно подключить и настроить различные платёжные системы для обработки онлайн-платежей.

### Компоненты проекта

**Проект включает следующие основные компоненты:**

- **Интеграции с платёжными системами**: каждая платёжная система имеет свой файл, который отвечает за обработку запросов и создание платежей.
- **Маршруты API**: маршруты для создания платежей и обработки webhook-уведомлений от платёжных систем.
- **Конфигурация**: хранение секретных ключей и других конфиденциальных данных через файл `.env`

### Зависимости

Для работы проекта требуется `Python 3.7` или выше.

- `FastAPI`
- `Uvicorn` (для запуска сервера)
- `Pydantic` (для валидации данных)
- `Requests` (для отправки HTTP-запросов к платёжным системам)
- `SQLAlchemy` (если используется база данных)

### Структура проекта

```
fastpay_connect/
│
├── app/
│   ├── __init__.py               # Инициализация приложения
│   ├── main.py                   # Главный файл для запуска FastAPI
│   ├── payment_gateways/         # Папка с интеграциями платёжных систем
│   │   ├── __init__.py
│   │   ├── yookassa.py           # Интеграция с ЮKassa
│   │   ├── tinkoff.py            # Интеграция с Tinkoff Касса
│   │   ├── cloudpayments.py      # Интеграция с CloudPayments
│   │   ├── unitpay.py            # Интеграция с UnitPay
│   │   └── robokassa.py          # Интеграция с Робокасса
│   ├── models/                   # Модели (если нужны для базы данных)
│   │   ├── __init__.py
│   │   └── payment.py            # Модели для платежей (опционально)
│   ├── routes/                   # Маршруты
│   │   ├── __init__.py
│   │   ├── payment_routes.py     # Маршруты для работы с платёжными системами
│   │   └── webhook_routes.py     # Маршруты для обработки уведомлений (webhook)
│   ├── utils/                    # Утилиты и вспомогательные функции
│   │   └── helpers.py            # Вспомогательные функции, например, для расчета подписи
│   ├── config.py                 # Конфигурации для разных платёжных систем
│   └── database.py               # Подключение к базе данных (если используется)
│
├── .env                          # Файл для хранения секретных ключей
├── requirements.txt              # Зависимости проекта
├── alembic/                      # Если используется миграция базы данных
│   └── versions/
├── README.md                     # Описание проекта
└── run.py                        # Точка входа для запуска приложения
```

### Описание изменений

1. `fastpay_connect` — это теперь основная папка проекта.
2. `main.py` — запускает FastAPI-приложение и подключает все маршруты для платёжных систем.
3. `payment_gateways/` — папка, где находятся интеграции с различными платёжными системами (`ЮKassa`, `Tinkoff`, `CloudPayments`, `UnitPay`, `Робокасса`).
4. Маршруты `payment_routes.py` и `webhook_routes.py` — определяют все взаимодействия с платёжными системами и обработку webhook-уведомлений.
5. `config.py` — хранит конфигурации для всех платёжных систем, которые будут использоваться в проекте.
6. `models/` — если будет нужна база данных, в этом каталоге будут храниться модели для хранения информации о платежах.
7. `helpers.py` — вспомогательные функции, такие как создание подписи, обработка ошибок и другие утилиты.
8. `.env` — файл для хранения всех конфиденциальных данных (например, API-ключей и секретных ключей).

**Для установки зависимостей выполните команду:**

```bash
pip install -r requirements.txt
```

### Настройка проекта

**Создание файла `.env`:**

```
YOOKASSA_API_KEY=your_yookassa_api_key
TINKOFF_API_KEY=your_tinkoff_api_key
CLOUDPAYMENTS_API_KEY=your_cloudpayments_api_key
UNITPAY_API_KEY=your_unitpay_api_key
ROBKASSA_API_KEY=your_robokassa_api_key
```

### Запуск приложения

**Для запуска приложения используйте команду:**

```
uvicorn app.main:app --reload
```

После этого вы сможете получить доступ к API, например, по адресу `http://127.0.0.1:8000`

### API Маршруты

**Создание платежа:**

- `POST /payments/yookassa`
- `POST /payments/tinkoff`
- `POST /payments/cloudpayments`
- `POST /payments/unitpay`
- `POST /payments/robokassa`

Каждый из этих маршрутов позволяет создать платёж с указанием суммы и описания.

**Обработка Webhook уведомлений:**

- `POST /webhooks/yookassa`
- `POST /webhooks/tinkoff`
- `POST /webhooks/cloudpayments`
- `POST /webhooks/unitpay`
- `POST /webhooks/robokassa`

### Описание переменных

`YOOKASSA_API_KEY`, `TINKOFF_API_KEY`, `CLOUDPAYMENTS_API_KEY`, `UNITPAY_API_KEY`, `ROBOKASSA_API_KEY` — ключи для авторизации и взаимодействия с платёжными системами. Замените эти значения на реальные ключи, полученные при регистрации в платёжных системах.

`DATABASE_URL` — строка подключения к базе данных. Пример с SQLite для локальной разработки и с PostgreSQL для продакшн окружения. Вы можете использовать любую другую базу данных по мере необходимости.

`SECRET_KEY` — секретный ключ для безопасности, например, для подписи сессий или JWT токенов.

`ALLOWED_HOSTS` — список хостов, которые могут подключаться к вашему серверу. Используйте это в целях безопасности, чтобы ограничить доступ только с определённых адресов.

`DEBUG` — флаг для включения/выключения режима отладки. Включайте его только в локальной разработке. На продакшн сервере должно быть установлено значение False.

`MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_SERVER`, `MAIL_PORT` — параметры для настройки почтового сервера, если приложение будет отправлять письма.
Эти маршруты предназначены для обработки уведомлений от платёжных систем о статусе транзакций.

**Автор:** Дуплей Максим Игоревич

**Дата:** 12.11.2024
