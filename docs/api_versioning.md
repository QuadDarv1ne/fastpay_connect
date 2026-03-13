# API Versioning

## Обзор

FastPay Connect поддерживает **версионирование API** для обеспечения обратной совместимости и плавной миграции между версиями.

## Поддерживаемые версии

| Версия | Статус | Срок поддержки |
|--------|--------|----------------|
| **v1** | ✅ Stable | До выхода v3 |
| **v2** | 🚧 Development | LTS |

## Способы указания версии

### 1. Через путь URL (Рекомендуется)

```bash
# API v1
GET /api/v1/payments/status/order_123
POST /api/v1/auth/login

# API v2
GET /api/v2/payments/status/order_123
POST /api/v2/auth/login
```

### 2. Через заголовок X-API-Version

```bash
curl -X GET "https://api.fastpay.com/payments/status/order_123" \
  -H "X-API-Version: v1"

curl -X POST "https://api.fastpay.com/auth/login" \
  -H "X-API-Version: v2" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret"
```

### 3. Через Accept header

```bash
# Version parameter
curl -X GET "https://api.fastpay.com/payments/status/order_123" \
  -H "Accept: application/json; version=v1"

# Media type versioning
curl -X GET "https://api.fastpay.com/payments/status/order_123" \
  -H "Accept: application/vnd.fastpay.v1+json"
```

## Приоритет определения версии

1. **Путь URL** (наивысший приоритет)
2. **Заголовок X-API-Version**
3. **Accept header** (низший приоритет)

## Обратная совместимость

### Legacy endpoints (без версии)

Следующие endpoints остаются доступными без указания версии для обратной совместимости:

- `/payments/*` - Платежи
- `/webhooks/*` - Webhook уведомления
- `/admin/payments/*` - Админ панель
- `/api/auth/*` - Аутентификация

**Рекомендация:** Используйте versioned endpoints (`/api/v1/*`) для новых проектов.

## Структура API v1

### Payments
```
POST   /api/v1/payments/create          - Создание платежа
GET    /api/v1/payments/status/{id}     - Статус платежа
```

### Webhooks
```
POST   /api/v1/webhooks/yookassa        - YooKassa webhook
POST   /api/v1/webhooks/tinkoff         - Tinkoff webhook
POST   /api/v1/webhooks/cloudpayments   - CloudPayments webhook
POST   /api/v1/webhooks/unitpay         - UnitPay webhook
POST   /api/v1/webhooks/robokassa       - Robokassa webhook
```

### Admin
```
GET    /api/v1/admin/payments/statistics    - Статистика
GET    /api/v1/admin/payments/dashboard     - Дашборд
GET    /api/v1/admin/payments/{order_id}    - Информация о платеже
POST   /api/v1/admin/payments/refund        - Возврат
POST   /api/v1/admin/payments/cancel        - Отмена
```

### Authentication
```
POST   /api/v1/auth/register            - Регистрация
POST   /api/v1/auth/login               - Login (form-data)
POST   /api/v1/auth/login/json          - Login (JSON)
POST   /api/v1/auth/refresh             - Обновление токена
GET    /api/v1/auth/me                  - Информация о пользователе
POST   /api/v1/auth/change-password     - Смена пароля
POST   /api/v1/auth/logout              - Logout
```

### Health Checks
```
GET    /api/v1/health                   - Проверка здоровья
GET    /api/v1/ready                    - Проверка готовности
GET    /api/v1/celery                   - Celery health
```

## API v2 (в разработке)

API v2 находится в разработке и включает следующие улучшения:

- Улучшенная пагинация
- GraphQL поддержка
- WebSocket уведомления
- Multi-tenant архитектура

```bash
GET /api/v2/  # Информация о версии
```

## Ответ API

Все versioned endpoints возвращают заголовок `X-API-Version`:

```http
HTTP/1.1 200 OK
X-API-Version: v1
Content-Type: application/json

{
  "data": {...}
}
```

## Миграция между версиями

### С v1 на v2 (когда выйдет)

1. Обновите клиентские библиотеки
2. Протестируйте endpoints на staging
3. Измените версию в запросах:
   ```bash
   # Было
   X-API-Version: v1
   
   # Стало
   X-API-Version: v2
   ```

### Deprecation Policy

- Старые версии поддерживаются минимум **12 месяцев** после выхода новой
- За **6 месяцев** до отключения версии отправляются уведомления
- Legacy endpoints (без версии) будут отключены в v3

## Примеры использования

### Python (httpx)

```python
import httpx

async def create_payment():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/api/v1/payments/create",
            json={
                "amount": 1000.00,
                "description": "Оплата заказа",
            },
            headers={"X-API-Version": "v1"}
        )
        return response.json()
```

### JavaScript (fetch)

```javascript
async function getPaymentStatus(orderId) {
    const response = await fetch(`/api/v1/payments/status/${orderId}`, {
        headers: {
            'X-API-Version': 'v1',
            'Accept': 'application/json'
        }
    });
    return await response.json();
}
```

### cURL

```bash
# Создание платежа
curl -X POST "http://localhost:8080/api/v1/payments/create" \
  -H "X-API-Version: v1" \
  -H "Content-Type: application/json" \
  -d '{"amount": 1000, "description": "Test"}'

# Получение статистики с токеном
curl -X GET "http://localhost:8080/api/v1/admin/payments/statistics" \
  -H "X-API-Version: v1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Тестирование

API versioning полностью протестирован:

```bash
# Запуск тестов для versioned endpoints
pytest tests/test_api_versioning.py -v
```

## Troubleshooting

### Ошибка: "API version required"

Убедитесь, что версия указана одним из способов:
- Добавьте `/api/v1/` или `/api/v2/` в путь
- Добавьте заголовок `X-API-Version: v1`
- Используйте `Accept: application/json; version=v1`

### Ошибка: "Unsupported API version"

Проверьте поддерживаемые версии:
- v1 ✅
- v2 🚧 (development)

### Legacy endpoints не работают

Legacy endpoints (`/payments/*` без версии) остаются доступными для обратной совместимости. Если они не работают, проверьте:
- Настройки middleware
- Логи приложения
- Конфигурация rate limiting

## Дополнительные ресурсы

- [OpenAPI спецификация](/docs)
- [Changelog](CHANGELOG.md)
- [Migration Guide](MIGRATION.md)
