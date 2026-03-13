# Webhook Retry Queue (Celery + Redis)

## Обзор

FastPay Connect использует **Celery** с **Redis** в качестве брокера сообщений для надёжной обработки webhook уведомлений от платёжных систем. Эта система обеспечивает:

- **Асинхронную обработку** webhook событий без блокировки основного приложения
- **Автоматические повторные попытки** (retry) при временных ошибках
- **Экспоненциальную задержку** между попытками (60s, 120s, 240s, 480s, 960s)
- **Идемпотентность** обработки через `webhook_event_id`
- **Мониторинг** через Flower и логи

## Архитектура

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│  Payment Gateway│────▶│  FastAPI App │────▶│     Redis       │
│   (YooKassa,    │     │  (Webhook    │     │   (Broker)      │
│    Tinkoff, etc)│     │   Endpoint)  │     │                 │
└─────────────────┘     └──────────────┘     └────────┬────────┘
                                                      │
                                                      ▼
                                             ┌─────────────────┐
                                             │  Celery Worker  │
                                             │  (Retry Logic)  │
                                             └────────┬────────┘
                                                      │
                                                      ▼
                                             ┌─────────────────┐
                                             │   Database      │
                                             │  (PostgreSQL/   │
                                             │   SQLite)       │
                                             └─────────────────┘
```

## Компоненты

### 1. Celery Tasks (`app/tasks/webhook_tasks.py`)

#### `process_webhook_task`
Основная задача для обработки webhook событий.

**Параметры:**
- `gateway`: Название платёжного шлюза (yookassa, tinkoff, cloudpayments, unitpay, robokassa)
- `payload`: Данные webhook от платёжной системы
- `auth_value`: Значение для аутентификации (сигнатура или токен)

**Retry логика:**
- **Максимум попыток:** 5
- **Задержка:** Экспоненциальная (60s × 2^retry_count)
- **Max delay:** 960 секунд (16 минут)

### 2. Webhook Routes (`app/routes/webhook_routes.py`)

Webhook endpoints автоматически ставят задачи в Celery очередь:

```python
POST /webhook/yookassa
POST /webhook/tinkoff
POST /webhook/cloudpayments
POST /webhook/unitpay
POST /webhook/robokassa
```

**Ответ при успешной постановке в очередь:**
```json
{
  "status": "queued",
  "message": "Webhook queued for processing"
}
```

### 3. Конфигурация (`app/settings.py`)

```python
# Redis / Celery
redis_url: str = "redis://localhost:6379/0"
celery_broker_url: str = "redis://localhost:6379/0"
celery_result_backend: str = "redis://localhost:6379/1"
celery_enabled: bool = True
```

## Запуск

### Локальная разработка

1. **Запустите Redis:**
```bash
# Docker
docker run -d -p 6379:6379 redis:7-alpine

# Или локально
redis-server
```

2. **Запустите Celery Worker:**
```bash
celery -A app.tasks.celery_app worker --loglevel=info --pool=solo
```

3. **Запустите Celery Beat (опционально, для периодических задач):**
```bash
celery -A app.tasks.celery_app beat --loglevel=info
```

4. **Запустите FastAPI приложение:**
```bash
uvicorn app.main:app --reload
```

### Docker Compose

```bash
# Development
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

**Сервисы:**
- `redis` - Redis брокер
- `app` - FastAPI приложение
- `celery_worker` - Celery worker для обработки webhook
- `celery_beat` - Celery beat для периодических задач

## Мониторинг

### Flower (Web UI для Celery)

Flower предоставляет веб-интерфейс для мониторинга Celery задач:

```bash
# Локально
celery -A app.tasks.celery_app flower --port=5555

# Docker Compose (production)
docker-compose -f docker-compose.prod.yml up flower
```

**URL:** http://localhost:5555

**Возможности:**
- Просмотр активных задач
- История выполненных задач
- Статистика по worker'ам
- Управление очередями

### Логи

Логи Celery worker записываются в стандартный вывод и могут быть просмотрены:

```bash
# Docker
docker-compose logs -f celery_worker

# Локально
# Вывод в консоль при запуске worker
```

## Обработка ошибок

### Сценарии

1. **Временная ошибка (таймаут, сеть):**
   - Автоматическая повторная попытка
   - Экспоненциальная задержка между попытками

2. **Постоянная ошибка (неверная сигнатура, invalid payload):**
   - После 5 попыток задача помечается как failed
   - Ошибка логируется
   - Статус платежа обновляется на "failed"

3. **Идемпотентность:**
   - Повторные webhook с тем же `webhook_event_id` игнорируются
   - Предотвращает дублирование обработки

### Логирование

```python
logger.info(f"Webhook queued to Celery: task_id={task.id}")
logger.warning(f"Retrying webhook processing in {delay}s (attempt {retry_count + 1}/{max_retries})")
logger.error(f"Webhook processing failed after {max_retries} retries: {exc}")
```

## Тестирование

### Интеграционные тесты

Тесты находятся в `tests/test_webhook_routes.py` и `tests/test_webhook_idempotency.py`.

```bash
pytest tests/test_webhook_routes.py -v
pytest tests/test_webhook_idempotency.py -v
```

### Ручное тестирование

1. Отправьте тестовый webhook:
```bash
curl -X POST http://localhost:8080/webhook/yookassa \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "test-123",
    "order_id": "order-456",
    "message": "payment successful"
  }'
```

2. Проверьте логи Celery worker
3. Проверьте статус платежа в БД

## Production настройки

### Оптимизация Celery Worker

```bash
# Количество worker процессов (рекомендуется: 2×CPU cores)
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

# С ограничением rate limit
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4 --autoscale=4,1
```

### Redis Persistence

Redis настроен с AOF (Append Only File) для сохранения данных:

```yaml
command: redis-server --appendonly yes
```

### Health Checks

```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `REDIS_URL` | URL подключения к Redis | `redis://localhost:6379/0` |
| `CELERY_BROKER_URL` | URL брокера Celery | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | URL для результатов задач | `redis://localhost:6379/1` |
| `CELERY_ENABLED` | Включить Celery обработку | `True` |

## Troubleshooting

### Worker не обрабатывает задачи

1. Проверьте подключение к Redis:
```bash
redis-cli ping  # Должен вернуть PONG
```

2. Проверьте, что worker запущен:
```bash
celery -A app.tasks.celery_app inspect ping
```

### Задачи застревают в очереди

1. Проверьте очередь через Flower
2. Увеличьте количество worker процессов
3. Проверьте логи на наличие ошибок

### Ошибки подключения к БД

Убедитесь, что Celery worker имеет доступ к той же БД, что и основное приложение.

## Дополнительные задачи

### `cleanup_old_webhook_events`
Периодическая задача для очистки старых webhook событий.

### `health_check`
Проверка работоспособности Celery worker.

### `send_webhook_retry_notification`
Отправка уведомлений о неудачных попытках обработки (для интеграции с Slack, email, etc.)

## Безопасность

- **IP Whitelist:** Webhook endpoints проверяют IP адреса платёжных систем
- **Signature Verification:** Подписи webhook проверяются перед обработкой
- **Idempotency:** Повторные события с тем же ID игнорируются

## Миграция с синхронной обработки

Если вы использовали синхронную обработку webhook, система автоматически переключится на асинхронную при наличии Celery.

Для отключения Celery и возврата к синхронной обработке:

```python
# settings.py
celery_enabled: bool = False
```

Или в webhook_routes.py:

```python
result, _ = await process_webhook(config, payload, auth_value, repository, use_celery=False)
```
