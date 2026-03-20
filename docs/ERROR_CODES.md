# Error Codes Documentation

> Полная документация всех ошибок API FastPay Connect

---

## 📋 Содержание

- [HTTP Status Codes](#-http-status-codes)
- [Error Response Format](#-error-response-format)
- [Payment Errors](#-payment-errors)
- [Authentication Errors](#-authentication-errors)
- [Validation Errors](#-validation-errors)
- [Webhook Errors](#-webhook-errors)
- [Rate Limiting Errors](#-rate-limiting-errors)
- [Database Errors](#-database-errors)
- [Gateway-Specific Errors](#-gateway-specific-errors)

---

## 🔢 HTTP Status Codes

| Code | Status | Description |
|------|--------|-------------|
| 200 | OK | Запрос успешно выполнен |
| 201 | Created | Ресурс успешно создан |
| 204 | No Content | Запрос выполнен, данных нет |
| 400 | Bad Request | Неверный запрос |
| 401 | Unauthorized | Требуется аутентификация |
| 403 | Forbidden | Доступ запрещён |
| 404 | Not Found | Ресурс не найден |
| 405 | Method Not Allowed | Метод не разрешён |
| 409 | Conflict | Конфликт состояния |
| 422 | Unprocessable Entity | Ошибка валидации |
| 429 | Too Many Requests | Превышен лимит запросов |
| 500 | Internal Server Error | Внутренняя ошибка сервера |
| 502 | Bad Gateway | Ошибка шлюза |
| 503 | Service Unavailable | Сервис недоступен |

---

## 📦 Error Response Format

### Стандартный формат ошибки

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Человекочитаемое описание",
    "details": {
      "field": "additional info"
    }
  }
}
```

### Примеры

**400 Bad Request:**
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Неверный формат запроса",
    "details": {
      "reason": "Missing required field: amount"
    }
  }
}
```

**422 Validation Error:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Ошибка валидации данных",
    "details": {
      "fields": {
        "amount": "must be greater than 0",
        "currency": "invalid currency code"
      }
    }
  }
}
```

---

## 💳 Payment Errors

### PAYMENT_001 — Payment Not Found
- **HTTP**: 404
- **Описание**: Платёж с указанным ID не найден
- **Решение**: Проверьте корректность payment_id

```json
{
  "error": {
    "code": "PAYMENT_001",
    "message": "Payment not found",
    "details": {
      "payment_id": "pay_12345"
    }
  }
}
```

### PAYMENT_002 — Invalid Amount
- **HTTP**: 400
- **Описание**: Неверная сумма платежа
- **Решение**: Сумма должна быть > 0

```json
{
  "error": {
    "code": "PAYMENT_002",
    "message": "Invalid payment amount",
    "details": {
      "amount": -100,
      "reason": "Amount must be greater than 0"
    }
  }
}
```

### PAYMENT_003 — Invalid Currency
- **HTTP**: 400
- **Описание**: Недопустимая валюта
- **Решение**: Используйте поддерживаемые валюты (RUB, USD, EUR, etc.)

```json
{
  "error": {
    "code": "PAYMENT_003",
    "message": "Invalid currency",
    "details": {
      "currency": "XXX",
      "supported": ["RUB", "USD", "EUR", "KZT", "BYN", "CNY", "TRY", "AED", "GBP", "JPY"]
    }
  }
}
```

### PAYMENT_004 — Payment Already Processed
- **HTTP**: 409
- **Описание**: Платёж уже обработан
- **Решение**: Не пытайтесь обработать платёж повторно

```json
{
  "error": {
    "code": "PAYMENT_004",
    "message": "Payment already processed",
    "details": {
      "payment_id": "pay_12345",
      "status": "completed"
    }
  }
}
```

### PAYMENT_005 — Payment Gateway Unavailable
- **HTTP**: 503
- **Описание**: Платёжный шлюз недоступен
- **Решение**: Повторите запрос позже

```json
{
  "error": {
    "code": "PAYMENT_005",
    "message": "Payment gateway unavailable",
    "details": {
      "gateway": "yookassa",
      "retry_after": 60
    }
  }
}
```

### PAYMENT_006 — Insufficient Funds
- **HTTP**: 402
- **Описание**: Недостаточно средств
- **Решение**: Проверьте баланс карты/счёта

```json
{
  "error": {
    "code": "PAYMENT_006",
    "message": "Insufficient funds",
    "details": {
      "required": 1000,
      "available": 500
    }
  }
}
```

### PAYMENT_007 — Payment Cancelled
- **HTTP**: 400
- **Описание**: Платёж отменён пользователем
- **Решение**: Создайте новый платёж

```json
{
  "error": {
    "code": "PAYMENT_007",
    "message": "Payment cancelled by user",
    "details": {
      "payment_id": "pay_12345"
    }
  }
}
```

### PAYMENT_008 — Refund Failed
- **HTTP**: 400
- **Описание**: Ошибка возврата средств
- **Решение**: Проверьте статус платежа и сумму возврата

```json
{
  "error": {
    "code": "PAYMENT_008",
    "message": "Refund failed",
    "details": {
      "reason": "Refund amount exceeds payment amount",
      "payment_amount": 1000,
      "refund_amount": 1500
    }
  }
}
```

---

## 🔐 Authentication Errors

### AUTH_001 — Unauthorized
- **HTTP**: 401
- **Описание**: Требуется аутентификация
- **Решение**: Добавьте valid JWT token

```json
{
  "error": {
    "code": "AUTH_001",
    "message": "Authentication required",
    "details": {
      "header": "Authorization",
      "format": "Bearer <token>"
    }
  }
}
```

### AUTH_002 — Invalid Token
- **HTTP**: 401
- **Описание**: Неверный токен
- **Решение**: Проверьте токен или получите новый

```json
{
  "error": {
    "code": "AUTH_002",
    "message": "Invalid or expired token",
    "details": {
      "reason": "Token expired",
      "expired_at": "2024-01-01T00:00:00Z"
    }
  }
}
```

### AUTH_003 — Forbidden
- **HTTP**: 403
- **Описание**: Недостаточно прав
- **Решение**: Требуется роль admin

```json
{
  "error": {
    "code": "AUTH_003",
    "message": "Insufficient permissions",
    "details": {
      "required_role": "admin",
      "current_role": "user"
    }
  }
}
```

### AUTH_004 — Invalid Credentials
- **HTTP**: 401
- **Описание**: Неверные учётные данные
- **Решение**: Проверьте логин/пароль

```json
{
  "error": {
    "code": "AUTH_004",
    "message": "Invalid credentials",
    "details": {
      "reason": "Username or password incorrect"
    }
  }
}
```

### AUTH_005 — Token Refresh Failed
- **HTTP**: 400
- **Описание**: Ошибка обновления токена
- **Решение**: Используйте valid refresh token

```json
{
  "error": {
    "code": "AUTH_005",
    "message": "Token refresh failed",
    "details": {
      "reason": "Refresh token expired or invalid"
    }
  }
}
```

---

## ✅ Validation Errors

### VAL_001 — Missing Required Field
- **HTTP**: 422
- **Описание**: Отсутствует обязательное поле
- **Решение**: Добавьте все required поля

```json
{
  "error": {
    "code": "VAL_001",
    "message": "Missing required field",
    "details": {
      "field": "amount",
      "type": "number",
      "required": true
    }
  }
}
```

### VAL_002 — Invalid Field Format
- **HTTP**: 422
- **Описание**: Неверный формат поля
- **Решение**: Проверьте формат данных

```json
{
  "error": {
    "code": "VAL_002",
    "message": "Invalid field format",
    "details": {
      "field": "email",
      "value": "invalid-email",
      "expected": "email format"
    }
  }
}
```

### VAL_003 — Field Value Out of Range
- **HTTP**: 422
- **Описание**: Значение вне допустимого диапазона
- **Решение**: Используйте значения в диапазоне

```json
{
  "error": {
    "code": "VAL_003",
    "message": "Value out of range",
    "details": {
      "field": "amount",
      "value": -100,
      "min": 0,
      "max": 1000000
    }
  }
}
```

### VAL_004 — Invalid JSON
- **HTTP**: 400
- **Описание**: Неверный JSON формат
- **Решение**: Проверьте синтаксис JSON

```json
{
  "error": {
    "code": "VAL_004",
    "message": "Invalid JSON format",
    "details": {
      "reason": "Unexpected token at line 3"
    }
  }
}
```

---

## 📡 Webhook Errors

### WH_001 — Invalid Signature
- **HTTP**: 401
- **Описание**: Неверная подпись webhook
- **Решение**: Проверьте secret key

```json
{
  "error": {
    "code": "WH_001",
    "message": "Invalid webhook signature",
    "details": {
      "gateway": "rustore",
      "header": "X-Signature"
    }
  }
}
```

### WH_002 — Missing Signature
- **HTTP**: 400
- **Описание**: Отсутствует подпись webhook
- **Решение**: Добавьте заголовок подписи

```json
{
  "error": {
    "code": "WH_002",
    "message": "Missing webhook signature",
    "details": {
      "required_header": "X-Signature"
    }
  }
}
```

### WH_003 — Invalid IP
- **HTTP**: 403
- **Описание**: IP не в whitelist
- **Решение**: Проверьте настройки whitelist

```json
{
  "error": {
    "code": "WH_003",
    "message": "IP not in whitelist",
    "details": {
      "ip": "1.2.3.4",
      "gateway": "yookassa",
      "whitelist": ["77.75.153.0/24"]
    }
  }
}
```

### WH_004 — Duplicate Event
- **HTTP**: 409
- **Описание**: Событие уже обработано
- **Решение**: Игнорируйте дубликат

```json
{
  "error": {
    "code": "WH_004",
    "message": "Duplicate webhook event",
    "details": {
      "event_id": "evt_12345",
      "processed_at": "2024-01-01T12:00:00Z"
    }
  }
}
```

### WH_005 — Invalid Timestamp
- **HTTP**: 400
- **Описание**: Timestamp истёк или неверен
- **Решение**: Синхронизируйте время

```json
{
  "error": {
    "code": "WH_005",
    "message": "Webhook timestamp invalid",
    "details": {
      "timestamp": "2024-01-01T00:00:00Z",
      "max_age_seconds": 300,
      "age_seconds": 600
    }
  }
}
```

---

## 🚦 Rate Limiting Errors

### RL_001 — Rate Limit Exceeded
- **HTTP**: 429
- **Описание**: Превышен лимит запросов
- **Решение**: Подождите Retry-After секунд

```json
{
  "error": {
    "code": "RL_001",
    "message": "Rate limit exceeded",
    "details": {
      "limit": "10/minute",
      "retry_after": 45,
      "reset_at": "2024-01-01T12:01:00Z"
    }
  }
}
```

### RL_002 — API Key Limit Exceeded
- **HTTP**: 429
- **Описание**: Превышен лимит для API ключа
- **Решение**: Используйте другой ключ или подождите

```json
{
  "error": {
    "code": "RL_002",
    "message": "API key rate limit exceeded",
    "details": {
      "api_key": "key_***1234",
      "limit": "100/minute",
      "retry_after": 30
    }
  }
}
```

---

## 🗄️ Database Errors

### DB_001 — Connection Failed
- **HTTP**: 503
- **Описание**: Ошибка подключения к БД
- **Решение**: Проверьте доступность БД

```json
{
  "error": {
    "code": "DB_001",
    "message": "Database connection failed",
    "details": {
      "reason": "Connection timeout",
      "retry_after": 10
    }
  }
}
```

### DB_002 — Record Not Found
- **HTTP**: 404
- **Описание**: Запись не найдена
- **Решение**: Проверьте ID записи

```json
{
  "error": {
    "code": "DB_002",
    "message": "Record not found",
    "details": {
      "table": "payments",
      "id": "pay_12345"
    }
  }
}
```

### DB_003 — Duplicate Entry
- **HTTP**: 409
- **Описание**: Дублирующаяся запись
- **Решение**: Используйте уникальный ID

```json
{
  "error": {
    "code": "DB_003",
    "message": "Duplicate entry",
    "details": {
      "field": "order_id",
      "value": "order_123"
    }
  }
}
```

---

## 🏦 Gateway-Specific Errors

### YooKassa Errors

| Code | HTTP | Description |
|------|------|-------------|
| YK_001 | 400 | Invalid shop_id or secret_key |
| YK_002 | 400 | Invalid payment scenario |
| YK_003 | 404 | Payment not found in YooKassa |
| YK_004 | 400 | Invalid refund amount |

### Tinkoff Errors

| Code | HTTP | Description |
|------|------|-------------|
| TK_001 | 400 | Invalid terminal key |
| TK_002 | 400 | Invalid order ID format |
| TK_003 | 400 | Amount exceeds limit |
| TK_004 | 400 | Invalid notification type |

### CloudPayments Errors

| Code | HTTP | Description |
|------|------|-------------|
| CP_001 | 400 | Invalid public ID |
| CP_002 | 400 | Invalid transaction ID |
| CP_003 | 400 | Recurrent payment failed |

### RuStore Errors

| Code | HTTP | Description |
|------|------|-------------|
| RS_001 | 400 | Invalid application ID |
| RS_002 | 400 | Invalid order state |
| RS_003 | 400 | Payment already refunded |

### SBP Errors

| Code | HTTP | Description |
|------|------|-------------|
| SBP_001 | 400 | Invalid merchant ID |
| SBP_002 | 400 | Bank not found |
| SBP_003 | 400 | QR code generation failed |

---

## 🔧 Troubleshooting

### Частые проблемы и решения

**1. 401 Unauthorized при webhook**
- Проверьте secret key в .env
- Убедитесь что заголовок X-Signature присутствует
- Проверьте формат подписи (hex/base64)

**2. 429 Too Many Requests**
- Увеличьте лимиты в настройках
- Реализуйте exponential backoff
- Используйте API key для повышенных лимитов

**3. 404 Payment Not Found**
- Проверьте payment_id в запросе
- Убедитесь что платёж существует в БД
- Проверьте tenant_id если используется multi-tenancy

**4. 403 IP Not Allowed**
- Добавьте IP шлюза в whitelist
- Проверьте настройки firewall
- Для локальной разработки используйте 127.0.0.1

---

## 📞 Support

Если вы столкнулись с ошибкой, которой нет в документации:

1. Проверьте логи приложения
2. Проверьте статус сервисов: `/health`
3. Откройте issue на GitHub

**GitHub Issues**: https://github.com/QuadDarv1ne/fastpay_connect/issues

---

*Последнее обновление: Mar 2026*
