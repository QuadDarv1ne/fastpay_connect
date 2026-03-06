# FastPay Connect

![FastPay Connect](fastpay_connect.png)

**FastPay Connect** — это проект для демонстрации интеграции различных платёжных систем с использованием `FastAPI`.

## 🔗 Интеграции

Проект поддерживает следующие платёжные системы:

- **ЮKassa** (бывшая Яндекс.Касса)
- **Tinkoff Касса**
- **CloudPayments**
- **UnitPay**
- **Робокасса**

## 🚀 Быстрый старт

```bash
# Клонирование репозитория
git clone https://github.com/yourusername/fastpay_connect.git
cd fastpay_connect

# Установка зависимостей
pip install -r requirements.txt

# Копирование .env.example
cp .env.example .env

# Запуск приложения
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 📚 О проекте

FastPay Connect служит учебным материалом и демонстрационным примером того, как подключить и настроить различные платёжные системы для обработки онлайн-платежей.

---

## 📁 Структура проекта

```plaintext
fastpay_connect/
│
├── app/
│   ├── __init__.py               # Инициализация приложения
│   ├── main.py                   # Главный файл для запуска FastAPI
│   ├── payment_gateways/         # Интеграции платёжных систем
│   │   ├── yookassa.py           # ЮKassa
│   │   ├── tinkoff.py            # Tinkoff Касса
│   │   ├── cloudpayments.py      # CloudPayments
│   │   ├── unitpay.py            # UnitPay
│   │   └── robokassa.py          # Робокасса
│   ├── routes/                   # Маршруты
│   │   ├── payment_routes.py     # Работа с платёжными системами
│   │   └── webhook_routes.py     # Обработка webhook-уведомлений
│   ├── utils/                    # Вспомогательные функции
│   ├── config.py                 # Конфигурации платёжных систем (legacy)
│   ├── settings.py               # Настройки на основе Pydantic
│   └── database.py               # Подключение к базе данных
│
├── k8s/                          # Kubernetes манифесты → deploy/k8s/
├── nginx/                        # Nginx конфигурация → deploy/nginx/
├── scripts/                      # Скрипты деплоя → deploy/scripts/
├── tests/                        # Тесты
├── .env                          # Конфиденциальные данные
├── .env.example                  # Пример .env
├── requirements.txt              # Зависимости проекта
├── README.md                     # Описание проекта
├── DEPLOYMENT.md                 # 📦 Руководство по деплою
├── docker-compose.yml            # Docker Compose (development)
├── docker-compose.prod.yml       # Docker Compose (production)
├── Dockerfile                    # Docker образ
├── deploy/                       # 📁 Файлы для деплоя
│   ├── Makefile                  # Автоматизация задач
│   ├── Procfile                  # Heroku/Railway команды
│   ├── render.yaml               # Render конфигурация
│   ├── railway.json              # Railway конфигурация
│   ├── fly.toml                  # Fly.io конфигурация
│   ├── cloudflare/               # Cloudflare Workers/Pages
│   ├── k8s/                      # Kubernetes манифесты
│   ├── aws/                      # AWS Elastic Beanstalk
│   ├── gcp/                      # Google Cloud Platform
│   └── nginx/                    # Nginx конфигурация
└── run.py                        # Точка входа для запуска приложения
```

---

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

---

### Настройка проекта

**Создание файла `.env`:**

```
YOOKASSA_API_KEY=your_yookassa_api_key
TINKOFF_API_KEY=your_tinkoff_api_key
CLOUDPAYMENTS_API_KEY=your_cloudpayments_api_key
UNITPAY_API_KEY=your_unitpay_api_key
ROBKASSA_API_KEY=your_robokassa_api_key
```

---

### Запуск приложения

**Для запуска приложения используйте команду:**

```
uvicorn app.main:app --reload
```

После этого вы сможете получить доступ к API, например, по адресу `http://127.0.0.1:8000`

---

### API Маршруты

### 1. Создание платежа

Каждый платёжный шлюз имеет свой собственный маршрут для создания платежа. Для создания платежа необходимо отправить POST-запрос с необходимыми параметрами.

#### Создание платежа через ЮKassa

- **URL:** `/payments/yookassa`
- **Метод:** `POST`
- **Тело запроса (JSON):**
    ```json
    {
      "amount": 1000,
      "currency": "RUB",
      "description": "Оплата за курс по Python"
    }
    ```

#### Создание платежа через Tinkoff

- **URL:** `/payments/tinkoff`
- **Метод:** `POST`
- **Тело запроса (JSON):**
    ```json
    {
      "amount": 2000,
      "currency": "RUB",
      "description": "Оплата за курс по C++"
    }
    ```

#### Создание платежа через CloudPayments

- **URL:** `/payments/cloudpayments`
- **Метод:** `POST`
- **Тело запроса (JSON):**
    ```json
    {
      "amount": 1500,
      "currency": "RUB",
      "description": "Оплата за курс по JavaScript"
    }
    ```

#### Создание платежа через UnitPay

- **URL:** `/payments/unitpay`
- **Метод:** `POST`
- **Тело запроса (JSON):**
    ```json
    {
      "amount": 500,
      "currency": "RUB",
      "description": "Оплата за курс по PHP"
    }
    ```

#### Создание платежа через Робокасса

- **URL:** `/payments/robokassa`
- **Метод:** `POST`
- **Тело запроса (JSON):**
    ```json
    {
      "amount": 1200,
      "currency": "RUB",
      "description": "Оплата за курс по Go"
    }
    ```

---

### 2. Обработка Webhook уведомлений

Для каждой платёжной системы предусмотрены маршруты для обработки уведомлений о статусе транзакций (webhook).

#### Обработка webhook уведомлений от ЮKassa

- **URL:** `/webhooks/yookassa`
- **Метод:** `POST`
- **Тело запроса (JSON):**
    ```json
    {
      "payment_id": "123456789",
      "status": "success",
      "amount": 1000,
      "currency": "RUB",
      "transaction_id": "TX123456789"
    }
    ```

#### Обработка webhook уведомлений от Tinkoff

- **URL:** `/webhooks/tinkoff`
- **Метод:** `POST`
- **Тело запроса (JSON):**
    ```json
    {
      "order_id": "123456789",
      "status": "success",
      "amount": 2000,
      "currency": "RUB",
      "transaction_id": "TX987654321"
    }
    ```

#### Обработка webhook уведомлений от CloudPayments

- **URL:** `/webhooks/cloudpayments`
- **Метод:** `POST`
- **Тело запроса (JSON):**
    ```json
    {
      "payment_id": "123456789",
      "status": "success",
      "amount": 1500,
      "currency": "RUB",
      "transaction_id": "TX543210987"
    }
    ```

#### Обработка webhook уведомлений от UnitPay

- **URL:** `/webhooks/unitpay`
- **Метод:** `POST`
- **Тело запроса (JSON):**
    ```json
    {
      "payment_id": "987654321",
      "status": "success",
      "amount": 500,
      "currency": "RUB",
      "transaction_id": "TX135792468"
    }
    ```

#### Обработка webhook уведомлений от Робокасса

- **URL:** `/webhooks/robokassa`
- **Метод:** `POST`
- **Тело запроса (JSON):**
    ```json
    {
      "order_id": "987654321",
      "status": "success",
      "amount": 1200,
      "currency": "RUB",
      "transaction_id": "TX246813579"
    }
    ```

---

### Ответы на запросы

Каждый из маршрутов возвратит стандартный ответ в формате JSON:

- **Успех (200 OK)**:
    ```json
    {
      "status": "success",
      "message": "Платёж успешно создан"
    }
    ```

- **Ошибка (400 Bad Request)**:
    ```json
    {
      "status": "error",
      "message": "Неверные данные в запросе"
    }
    ```

- **Ошибка (500 Internal Server Error)**:
    ```json
    {
      "status": "error",
      "message": "Ошибка сервера"
    }
    ```

---

### Примечание

Для выполнения запросов к API необходимо настроить и указать API-ключи для каждой платёжной системы в файле `.env`, как указано в [секции настройки проекта](###настройка-проекта).

---

## Инструкция по получению API-ключей

### ЮKassa (бывшая Яндекс.Касса) 🏦
1. Перейдите на сайт [ЮKassa](https://kassa.yandex.ru/).
2. Зарегистрируйтесь или войдите в личный кабинет.
3. В разделе "Интеграции" выберите "API" и создайте новый API-ключ.
4. Сохраните ключ в безопасном месте 🔒.

### Tinkoff Касса 💳
1. Перейдите на сайт [Tinkoff API](https://www.tinkoff.ru/business/payments/api/).
2. Зарегистрируйтесь в личном кабинете.
3. В разделе "Настройки" получите публичный и секретный API-ключи.

### CloudPayments ☁️💳
1. Перейдите на сайт [CloudPayments](https://www.cloudpayments.ru/).
2. Зарегистрируйтесь и войдите в личный кабинет.
3. В разделе "Настройки" получите API-ключи.

### UnitPay 📱
1. Перейдите на сайт [UnitPay](https://unitpay.ru/).
2. Зарегистрируйтесь и создайте аккаунт.
3. В разделе "Настройки" найдите свой API-ключ.

### Робокасса 💰
1. Перейдите на сайт [Робокасса](https://www.robokassa.ru/).
2. Зарегистрируйтесь и войдите в личный кабинет.
3. В разделе "Настройки" получите API-ключи.

### Советы по безопасности 🔐
- Храните ключи в безопасном месте, например, в переменных окружения или секретных хранилищах.
- Никогда не размещайте ключи в публичных репозиториях 🚫.

---

## 📦 Деплой

Проект поддерживает развёртывание на различных платформах:

### 🐳 Docker

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

### ☁️ Cloud платформы

| Платформа | Команда | Документация |
|-----------|---------|--------------|
| **Render** | `renderctl deploy` | [deploy/render.yaml](deploy/render.yaml) |
| **Railway** | `railway up` | [deploy/railway.json](deploy/railway.json) |
| **Fly.io** | `fly deploy` | [deploy/fly.toml](deploy/fly.toml) |
| **Heroku** | `git push heroku main` | [deploy/Procfile](deploy/Procfile) |
| **Google Cloud Run** | `gcloud run deploy` | [deploy/gcp/cloudbuild.yaml](deploy/gcp/cloudbuild.yaml) |
| **AWS Elastic Beanstalk** | `eb deploy` | [deploy/aws/](deploy/aws/) |
| **Kubernetes** | `kubectl apply -f deploy/k8s/` | [deploy/k8s/deployment.yaml](deploy/k8s/deployment.yaml) |
| **Cloudflare Workers** | `wrangler deploy` | [deploy/cloudflare/wrangler.toml](deploy/cloudflare/wrangler.toml) |
| **Cloudflare Pages** | `wrangler pages deploy` | [DEPLOYMENT.md](DEPLOYMENT.md#cloudflare-pages) |

### 📖 Подробное руководство

Смотрите [**DEPLOYMENT.md**](DEPLOYMENT.md) для полной документации по деплою.

---

### ⚙️ Конфигурация

`YOOKASSA_API_KEY`, `TINKOFF_API_KEY`, `CLOUDPAYMENTS_API_KEY`, `UNITPAY_API_KEY`, `ROBOKASSA_API_KEY` — ключи для авторизации и взаимодействия с платёжными системами. Замените эти значения на реальные ключи, полученные при регистрации в платёжных системах.

`DATABASE_URL` — строка подключения к базе данных. Пример с SQLite для локальной разработки и с PostgreSQL для продакшн окружения. Вы можете использовать любую другую базу данных по мере необходимости.

`SECRET_KEY` — секретный ключ для безопасности, например, для подписи сессий или JWT токенов.

`ALLOWED_HOSTS` — список хостов, которые могут подключаться к вашему серверу. Используйте это в целях безопасности, чтобы ограничить доступ только с определённых адресов.

`DEBUG` — флаг для включения/выключения режима отладки. Включайте его только в локальной разработке. На продакшн сервере должно быть установлено значение False.

`MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_SERVER`, `MAIL_PORT` — параметры для настройки почтового сервера, если приложение будет отправлять письма.
Эти маршруты предназначены для обработки уведомлений от платёжных систем о статусе транзакций.

---

### 📄 Лицензия

[Этот проект лицензирован под лицензией MIT](LICENSE)

Для получения дополнительной информации ознакомьтесь с файлом `LICENSE`

---

### Автор

**Дуплей Максим Игоревич**

**Дата:** 15.10.2024 - 30.10.2024

**Версия:** 1.0
