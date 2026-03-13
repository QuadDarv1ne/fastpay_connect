# WebSocket Notifications

## Обзор

FastPay Connect поддерживает **WebSocket уведомления** для получения real-time информации об изменениях статусов платежей.

## Возможности

- 🔔 **Real-time уведомления** о изменениях статуса платежа
- 📌 **Подписка на заказы** - получайте уведомления о конкретных заказах
- 🏦 **Подписка на gateway** - отслеживайте платежи по платёжным системам
- 💬 **Двусторонняя связь** - отправка команд через WebSocket
- 🔐 **JWT аутентификация** - безопасное подключение
- 📊 **Статистика подключений** - мониторинг активных сессий

## Подключение

### Базовое подключение

```javascript
const ws = new WebSocket(
  'ws://localhost:8080/ws/notifications?token=YOUR_JWT_TOKEN'
);

ws.onopen = () => {
  console.log('Connected to notifications');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};
```

### Подписка на заказ при подключении

```javascript
const ws = new WebSocket(
  'ws://localhost:8080/ws/notifications?token=YOUR_JWT_TOKEN&order_id=order_123'
);
```

### Подписка на gateway при подключении

```javascript
const ws = new WebSocket(
  'ws://localhost:8080/ws/notifications?token=YOUR_JWT_TOKEN&gateway=yookassa'
);
```

## Формат сообщений

### Приветственное сообщение

```json
{
  "type": "connected",
  "data": {
    "user_id": "1",
    "message": "Successfully connected to notifications"
  },
  "timestamp": "2026-03-13T12:00:00Z"
}
```

### Уведомление об изменении платежа

```json
{
  "type": "payment_updated",
  "data": {
    "order_id": "order_123",
    "payment_id": "pay_123",
    "status": "completed",
    "amount": 1000.00,
    "currency": "RUB",
    "gateway": "yookassa",
    "updated_at": "2026-03-13T12:00:00Z"
  },
  "timestamp": "2026-03-13T12:00:00Z"
}
```

### Уведомление о создании платежа

```json
{
  "type": "payment_created",
  "data": {
    "order_id": "order_123",
    "payment_id": "pay_123",
    "amount": 1000.00,
    "currency": "RUB",
    "gateway": "yookassa",
    "payment_url": "https://payment.yookassa.ru/...",
    "created_at": "2026-03-13T12:00:00Z"
  },
  "timestamp": "2026-03-13T12:00:00Z"
}
```

### Уведомление об ошибке

```json
{
  "type": "payment_error",
  "data": {
    "order_id": "order_123",
    "error": "Payment gateway timeout",
    "gateway": "yookassa",
    "timestamp": "2026-03-13T12:00:00Z"
  },
  "timestamp": "2026-03-13T12:00:00Z"
}
```

## Команды клиента

### Подписка на заказ

```javascript
ws.send(JSON.stringify({
  "action": "subscribe",
  "order_id": "order_123"
}));
```

**Ответ:**
```json
{
  "type": "subscribed",
  "data": {"order_id": "order_123"},
  "timestamp": "2026-03-13T12:00:00Z"
}
```

### Отписка от заказа

```javascript
ws.send(JSON.stringify({
  "action": "unsubscribe",
  "order_id": "order_123"
}));
```

**Ответ:**
```json
{
  "type": "unsubscribed",
  "data": {"order_id": "order_123"},
  "timestamp": "2026-03-13T12:00:00Z"
}
```

### Подписка на gateway

```javascript
ws.send(JSON.stringify({
  "action": "subscribe_gateway",
  "gateway": "yookassa"
}));
```

### Отписка от gateway

```javascript
ws.send(JSON.stringify({
  "action": "unsubscribe_gateway",
  "gateway": "yookassa"
}));
```

### Получить статистику

```javascript
ws.send(JSON.stringify({
  "action": "get_stats"
}));
```

**Ответ:**
```json
{
  "type": "stats",
  "data": {
    "total_connections": 5,
    "unique_users": 3,
    "order_subscriptions": 10,
    "gateway_subscriptions": 2
  },
  "timestamp": "2026-03-13T12:00:00Z"
}
```

## REST API

### Получить статистику подключений

```http
GET /ws/stats
Authorization: Bearer YOUR_JWT_TOKEN
```

**Ответ:**
```json
{
  "status": "success",
  "data": {
    "total_connections": 5,
    "unique_users": 3,
    "order_subscriptions": 10,
    "gateway_subscriptions": 2
  }
}
```

## Примеры использования

### JavaScript (Browser)

```javascript
class PaymentNotifier {
  constructor(token) {
    this.token = token;
    this.ws = null;
    this.reconnectDelay = 1000;
    this.reconnect();
  }

  connect() {
    this.ws = new WebSocket(
      `ws://localhost:8080/ws/notifications?token=${this.token}`
    );

    this.ws.onopen = () => {
      console.log('Connected');
      this.reconnectDelay = 1000;
    };

    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      this.handleMessage(message);
    };

    this.ws.onclose = () => {
      console.log('Disconnected, reconnecting...');
      setTimeout(() => this.reconnect(), this.reconnectDelay);
      this.reconnectDelay *= 2; // Exponential backoff
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  reconnect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.close();
    }
    this.connect();
  }

  handleMessage(message) {
    switch (message.type) {
      case 'connected':
        console.log('Connected:', message.data);
        break;
      case 'payment_updated':
        this.onPaymentUpdate(message.data);
        break;
      case 'payment_created':
        this.onPaymentCreated(message.data);
        break;
      case 'payment_error':
        this.onPaymentError(message.data);
        break;
    }
  }

  onPaymentUpdate(data) {
    console.log('Payment updated:', data);
    // Update UI, show notification, etc.
  }

  onPaymentCreated(data) {
    console.log('Payment created:', data);
    // Redirect to payment URL, etc.
  }

  onPaymentError(data) {
    console.error('Payment error:', data);
    // Show error notification
  }

  subscribeToOrder(orderId) {
    this.ws.send(JSON.stringify({
      action: 'subscribe',
      order_id: orderId
    }));
  }

  getStats() {
    this.ws.send(JSON.stringify({
      action: 'get_stats'
    }));
  }
}

// Usage
const notifier = new PaymentNotifier(jwtToken);
notifier.subscribeToOrder('order_123');
```

### Python

```python
import websocket
import json
import threading
import time

class PaymentNotifier:
    def __init__(self, token):
        self.token = token
        self.ws = None
        
    def connect(self):
        url = f"ws://localhost:8080/ws/notifications?token={self.token}"
        self.ws = websocket.WebSocketApp(
            url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.run_forever()
    
    def on_open(self, ws):
        print("Connected")
        
    def on_message(self, ws, message):
        data = json.loads(message)
        print(f"Received: {data}")
        
        if data["type"] == "connected":
            # Subscribe to order
            ws.send(json.dumps({
                "action": "subscribe",
                "order_id": "order_123"
            }))
    
    def on_error(self, ws, error):
        print(f"Error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        print(f"Disconnected: {close_status_code}")

# Usage
notifier = PaymentNotifier(jwt_token)
thread = threading.Thread(target=notifier.connect)
thread.start()
```

### cURL

```bash
# Подключение и отправка команды
websocat "ws://localhost:8080/ws/notifications?token=YOUR_TOKEN"

# В интерактивном режиме:
{"action": "subscribe", "order_id": "order_123"}
{"action": "get_stats"}
```

## Коды ошибок подключения

| Код | Описание |
|-----|----------|
| 4001 | Token required |
| 4002 | Invalid token |
| 4003 | Connection failed |

## Архитектура

### Connection Manager

```
┌─────────────────────────────────────────────────────────┐
│              WebSocket Connection Manager               │
├─────────────────────────────────────────────────────────┤
│  active_connections: {websocket: user_id}               │
│  user_connections: {user_id: [websockets]}              │
│  order_subscriptions: {order_id: [websockets]}          │
│  gateway_subscriptions: {gateway: [websockets]}         │
└─────────────────────────────────────────────────────────┘
```

### Notification Flow

```
Payment Status Change
        ↓
PaymentRepository.update_status()
        ↓
send_payment_notification()
        ↓
┌───────────────────────────────────┐
│  Broadcast to:                    │
│  - order_subscribers              │
│  - gateway_subscribers            │
└───────────────────────────────────┘
        ↓
WebSocket clients receive notification
```

## Безопасность

### Требования

- **JWT токен** обязателен для подключения
- Токен проверяется через `decode_token()`
- Подключение закрывается при невалидном токене

### Rate Limiting

WebSocket подключения не имеют rate limiting, но рекомендуется:
- Закрывать неиспользуемые подключения
- Не создавать более 5 подключений на пользователя

### Best Practices

1. **Всегда обрабатывайте onclose** - реализуйте reconnection logic
2. **Используйте exponential backoff** при переподключении
3. **Отписывайтесь от заказов** когда они больше не нужны
4. **Не храните чувствительные данные** в сообщениях

## Мониторинг

### Статистика подключений

```bash
curl -X GET "http://localhost:8080/ws/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Логи

```
INFO: WebSocket connected: user_id=1, total_connections=5
INFO: WebSocket subscribed to order: order_id=order_123
INFO: Sent 3 WebSocket notifications for payment order_123
INFO: WebSocket disconnected: user_id=1, total_connections=4
```

## Troubleshooting

### "WebSocket disconnect"

- Проверьте JWT токен
- Убедитесь что сервер запущен
- Проверьте firewall/proxy настройки

### "Not receiving notifications"

- Проверьте что подписались на правильный order_id
- Убедитесь что payment status действительно изменился
- Проверьте логи сервера

### "Too many connections"

- Закройте старые подключения
- Реализуйте connection pooling
- Используйте один connection для нескольких подписок

## Дополнительные ресурсы

- [WebSocket API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/)
- [GraphQL API](api_versioning.md)
