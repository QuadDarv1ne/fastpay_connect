# Webhook Retry Queue Monitoring Dashboard

## Обзор

FastPay Connect предоставляет **полнофункциональный dashboard** для мониторинга обработки webhook уведомлений с retry логикой.

## Возможности

- 📊 **Общая статистика** - количество событий по статусам и gateway
- ⏳ **Retry Queue** - события, ожидающие повторной обработки
- 📜 **Recent Events** - последние webhook события
- 📈 **Метрики** - данные для Prometheus
- 🔍 **Фильтрация** - по gateway, статусу, order_id
- 📱 **UI Dashboard** - веб-интерфейс для мониторинга

## API Endpoints

### Overview

```http
GET /api/monitoring/webhooks/overview?days=7
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "status": "success",
  "data": {
    "total": 100,
    "by_status": {
      "success": 80,
      "retry": 10,
      "failed": 10
    },
    "by_gateway": {
      "yookassa": 50,
      "tinkoff": 30,
      "cloudpayments": 20
    },
    "retrying": 10,
    "failed": 10,
    "period_days": 7
  }
}
```

### Dashboard

```http
GET /api/monitoring/webhooks/dashboard?limit=10
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "status": "success",
  "data": {
    "total_events": 100,
    "by_status": {...},
    "by_gateway": {...},
    "recent_events": [...],
    "retrying_count": 10,
    "failed_count": 10,
    "error_by_gateway": {...},
    "avg_processing_time": null
  }
}
```

### Events List

```http
GET /api/monitoring/webhooks/events?page=1&page_size=20&gateway=yookassa&status=success
Authorization: Bearer <token>
```

**Параметры:**
- `page` - номер страницы (default: 1)
- `page_size` - элементов на странице (1-100, default: 20)
- `gateway` - фильтр по платёжной системе (optional)
- `status` - фильтр по статусу (optional)

**Ответ:**
```json
{
  "status": "success",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "pages": 5
  }
}
```

### Event Detail

```http
GET /api/monitoring/webhooks/events/{event_id}
Authorization: Bearer <token>
```

### Events by Order

```http
GET /api/monitoring/webhooks/events/order/{order_id}
Authorization: Bearer <token>
```

### Retry Queue

```http
GET /api/monitoring/webhooks/retry-queue?limit=50
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "status": "success",
  "data": {
    "count": 5,
    "items": [
      {
        "event_id": "evt_123456",
        "order_id": "order_789",
        "gateway": "tinkoff",
        "status": "retry",
        "retry_count": 2,
        "max_retries": 5,
        "last_error": "Connection timeout",
        "next_retry_at": "2026-03-13T15:30:00Z"
      }
    ]
  }
}
```

### Metrics

```http
GET /api/monitoring/webhooks/metrics
Authorization: Bearer <token>
```

**Ответ:**
```json
{
  "status": "success",
  "data": {
    "total_webhooks_24h": 50,
    "by_gateway": {...},
    "by_status": {...},
    "retrying": 5,
    "failed": 2
  }
}
```

### Cleanup Old Events

```http
POST /api/monitoring/webhooks/cleanup?days=30
Authorization: Bearer <token>
```

**Параметры:**
- `days` - удалить события старше N дней (7-365, default: 30)

**Ответ:**
```json
{
  "status": "success",
  "message": "Deleted 150 old webhook events",
  "deleted_count": 150
}
```

## UI Dashboard

Веб-интерфейс доступен по адресу:

```
GET /api/monitoring/webhooks/dashboard-ui
Authorization: Bearer <token>
```

**Возможности UI:**
- Автоматическое обновление каждые 30 секунд
- Статистика в реальном времени
- Визуализация по gateway
- Список retry очереди
- Последние события

## Модели данных

### WebhookEventStatus

| Статус | Описание |
|--------|----------|
| `pending` | Ожидает обработки |
| `processing` | В процессе |
| `success` | Успешно обработано |
| `retry` | Требуется повторная попытка |
| `failed` | Обработка не удалась |

### WebhookEvent

| Поле | Тип | Описание |
|------|-----|----------|
| `event_id` | String | Уникальный ID события |
| `order_id` | String | ID заказа |
| `gateway` | String | Платёжная система |
| `status` | Enum | Статус события |
| `retry_count` | Integer | Количество попыток |
| `max_retries` | Integer | Максимум попыток |
| `last_error` | Text | Последняя ошибка |
| `next_retry_at` | DateTime | Время следующей попытки |
| `payload` | JSON | Исходный payload |
| `created_at` | DateTime | Время создания |
| `processed_at` | DateTime | Время успешной обработки |

## Retry Logic

### Экспоненциальная задержка

| Попытка | Задержка |
|---------|----------|
| 1 | 60s |
| 2 | 120s |
| 3 | 240s |
| 4 | 480s |
| 5 | 960s |

### Максимум попыток

По умолчанию **5 попыток**. После исчерпания:
- Событие помечается как `failed`
- Сохраняется в БД для анализа
- Требует ручного вмешательства

## Prometheus Metrics

Для интеграции с Prometheus используйте endpoint `/metrics`:

```prometheus
# Webhook metrics
fastpay_webhooks_total_24h{gateway="yookassa"} 50
fastpay_webhooks_success_total{gateway="yookassa"} 45
fastpay_webhooks_failed_total{gateway="yookassa"} 2
fastpay_webhooks_retrying_total{gateway="yookassa"} 3
```

## Примеры использования

### Python

```python
import httpx

async def get_webhook_stats(token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8080/api/monitoring/webhooks/overview",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

### cURL

```bash
# Получить статистику
curl -X GET "http://localhost:8080/api/monitoring/webhooks/overview?days=7" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Получить retry очередь
curl -X GET "http://localhost:8080/api/monitoring/webhooks/retry-queue" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Очистить старые события
curl -X POST "http://localhost:8080/api/monitoring/webhooks/cleanup?days=30" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## База данных

### Миграции

Для создания таблиц выполните:

```bash
alembic upgrade head
```

Создаются таблицы:
- `webhook_events` - события webhook
- `webhook_stats` - агрегированная статистика

### Индексы

```sql
-- webhook_events
CREATE INDEX ix_webhook_gateway ON webhook_events(gateway, created_at);
CREATE INDEX ix_webhook_status ON webhook_events(status);
CREATE INDEX ix_webhook_order ON webhook_events(order_id);
CREATE UNIQUE INDEX ix_webhook_event_id ON webhook_events(event_id);

-- webhook_stats
CREATE UNIQUE INDEX ix_stats_gateway_date ON webhook_stats(gateway, date);
```

## Безопасность

### Требования к доступу

- **Admin role** требуется для всех endpoints мониторинга
- OAuth2 токен обязателен
- Rate limiting применяется ко всем endpoints

### Rate Limits

| Endpoint | Лимит |
|----------|-------|
| `/overview` | 30/minute |
| `/dashboard` | 30/minute |
| `/events` | 100/minute |
| `/retry-queue` | 30/minute |
| `/metrics` | 30/minute |
| `/cleanup` | 10/hour |

## Troubleshooting

### Много событий в retry queue

1. Проверьте логи Celery worker
2. Убедитесь в доступности платёжных шлюзов
3. Проверьте настройки retry delay

### Высокий процент failed событий

1. Анализируйте `last_error` в событиях
2. Проверьте конфигурацию webhook шлюзов
3. Увеличьте `max_retries` при необходимости

### Dashboard не загружается

1. Проверьте токен авторизации
2. Убедитесь в наличии admin role
3. Проверьте логи приложения

## Дополнительные ресурсы

- [Celery Documentation](https://docs.celeryq.dev/)
- [Prometheus Metrics](https://prometheus.io/docs/concepts/metric_types/)
- [API Versioning](api_versioning.md)
