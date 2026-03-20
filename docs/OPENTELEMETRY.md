# OpenTelemetry Tracing Guide

> Distributed tracing для FastPay Connect с использованием OpenTelemetry

---

## 📋 Содержание

- [Быстрый старт](#-быстрый-старт)
- [Настройка экспортеров](#-настройка-экспортеров)
- [Интеграция с Jaeger](#-интеграция-с-jaeger)
- [Интеграция с Zipkin](#-интеграция-с-zipkin)
- [Интеграция с Grafana Tempo](#-интеграция-с-grafana-tempo)
- [Instrumentation](#-instrumentation)
- [Создание custom spans](#-создание-custom-spans)
- [Мониторинг и алерты](#-мониторинг-и-алерты)

---

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
# или
pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi
```

### 2. Включение трассировки

Добавьте в `.env`:

```env
# Включить OpenTelemetry
OPENTELEMETRY_ENABLED=true

# Тип экспортера: jaeger, otlp, console, none
OPENTELEMETRY_EXPORTER=console

# Endpoint (опционально, зависит от экспортера)
OPENTELEMETRY_ENDPOINT=http://localhost:4317
```

### 3. Запуск с Jaeger (Docker)

```bash
# Запуск Jaeger
docker run -d --name jaeger \
  -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
  -p 5775:5775/udp \
  -p 6831:6831/udp \
  -p 6832:6832/udp \
  -p 5778:5778 \
  -p 16686:16686 \
  -p 14268:14268 \
  -p 14250:14250 \
  -p 9411:9411 \
  jaegertracing/all-in-one:latest

# Запуск приложения
export OPENTELEMETRY_ENABLED=true
export OPENTELEMETRY_EXPORTER=jaeger
export JAEGER_ENDPOINT=http://localhost:14268/api/traces

uvicorn app.main:app --reload
```

### 4. Просмотр трассировок

Откройте Jaeger UI: http://localhost:16686

---

## 🔧 Настройка экспортеров

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `OPENTELEMETRY_ENABLED` | Включить трассировку | `false` |
| `OPENTELEMETRY_EXPORTER` | Тип экспортера | `console` |
| `OPENTELEMETRY_ENDPOINT` | URL экспортера | - |
| `JAEGER_ENDPOINT` | Jaeger endpoint | `http://jaeger:14268/api/traces` |
| `JAEGER_HOST` | Jaeger agent host | `jaeger` |
| `JAEGER_PORT` | Jaeger agent port | `6831` |
| `OTLP_ENDPOINT` | OTLP collector endpoint | `http://otel-collector:4317` |

### Типы экспортеров

**Console (для разработки):**
```env
OPENTELEMETRY_ENABLED=true
OPENTELEMETRY_EXPORTER=console
```

**Jaeger:**
```env
OPENTELEMETRY_ENABLED=true
OPENTELEMETRY_EXPORTER=jaeger
JAEGER_ENDPOINT=http://jaeger:14268/api/traces
```

**OTLP (OpenTelemetry Protocol):**
```env
OPENTELEMETRY_ENABLED=true
OPENTELEMETRY_EXPORTER=otlp
OTLP_ENDPOINT=http://otel-collector:4317
```

**None (отключить):**
```env
OPENTELEMETRY_ENABLED=false
# или
OPENTELEMETRY_EXPORTER=none
```

---

## 📊 Интеграция с Jaeger

### Docker Compose

Добавьте в `docker-compose.yml`:

```yaml
services:
  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: fastpay-jaeger
    restart: unless-stopped
    environment:
      - COLLECTOR_ZIPKIN_HOST_PORT=:9411
    ports:
      - "5775:5775/udp"
      - "6831:6831/udp"
      - "6832:6832/udp"
      - "5778:5778"
      - "16686:16686"  # UI
      - "14268:14268"  # Collector
      - "9411:9411"    # Zipkin compatible
    networks:
      - fastpay-network

  app:
    # ... ваша конфигурация
    environment:
      - OPENTELEMETRY_ENABLED=true
      - OPENTELEMETRY_EXPORTER=jaeger
      - JAEGER_ENDPOINT=http://jaeger:14268/api/traces
    depends_on:
      - jaeger
```

### Доступ к Jaeger UI

```
http://localhost:16686
```

---

## 📊 Интеграция с Zipkin

### Docker Compose

```yaml
services:
  zipkin:
    image: openzipkin/zipkin:latest
    container_name: fastpay-zipkin
    restart: unless-stopped
    ports:
      - "9411:9411"
    networks:
      - fastpay-network

  app:
    environment:
      - OPENTELEMETRY_ENABLED=true
      - OPENTELEMETRY_EXPORTER=otlp
      - OTLP_ENDPOINT=http://zipkin:9411/api/v2/spans
```

### Доступ к Zipkin UI

```
http://localhost:9411
```

---

## 📊 Интеграция с Grafana Tempo

### Docker Compose

```yaml
services:
  tempo:
    image: grafana/tempo:latest
    container_name: fastpay-tempo
    restart: unless-stopped
    command: ["-config.file=/etc/tempo.yaml"]
    volumes:
      - ./tempo-config.yaml:/etc/tempo.yaml
      - tempo-data:/tmp/tempo
    ports:
      - "14268:14268"  # Jaeger receiver
      - "4317:4317"    # OTLP gRPC
      - "3200:3200"    # Tempo API
    networks:
      - fastpay-network

  app:
    environment:
      - OPENTELEMETRY_ENABLED=true
      - OPENTELEMETRY_EXPORTER=otlp
      - OTLP_ENDPOINT=http://tempo:4317
```

### tempo-config.yaml

```yaml
stream_over_http_enabled: true
server:
  http_listen_port: 3200
distributor:
  receivers:
    jaeger:
      protocols:
        thrift_http:
    otlp:
      protocols:
        http:
        grpc:
storage:
  trace:
    backend: local
    local:
      path: /tmp/tempo/blocks
```

---

## 🔌 Instrumentation

OpenTelemetry автоматически инструментирует:

### FastAPI
- HTTP запросы/ответы
- Статус коды
- Duration
- Request/Response headers

### Redis
- Команды Redis
- Duration операций
- Connection info

### SQLAlchemy
- SQL запросы
- Duration выполнения
- Database info

### Celery
- Tasks execution
- Worker info
- Task duration

---

## 📝 Создание custom spans

### Basic Example

```python
from app.utils.opentelemetry import get_tracer

tracer = get_tracer(__name__)

@router.get("/payments/{payment_id}")
async def get_payment(payment_id: str):
    with tracer.start_as_current_span("get_payment") as span:
        span.set_attribute("payment.id", payment_id)
        
        payment = repository.get_by_id(payment_id)
        
        if payment:
            span.set_attribute("payment.status", payment.status.value)
            span.set_attribute("payment.amount", payment.amount)
        
        return payment
```

### Async Context

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def process_payment(payment_data):
    with tracer.start_as_current_span("process_payment") as span:
        span.set_attribute("payment.amount", payment_data.amount)
        span.set_attribute("payment.gateway", payment_data.gateway)
        
        # Ваш код
        result = await gateway.process(payment_data)
        
        span.set_attribute("payment.result", result.status)
        
        return result
```

### Adding Events

```python
with tracer.start_as_current_span("checkout") as span:
    span.add_event("checkout_started")
    
    # Step 1: Validate
    span.add_event("validation_complete", attributes={
        "valid": "true"
    })
    
    # Step 2: Process payment
    span.add_event("payment_processed", attributes={
        "gateway": "yookassa",
        "transaction_id": "txn_123"
    })
    
    # Step 3: Send notification
    span.add_event("notification_sent")
```

### Error Handling

```python
from opentelemetry.trace import Status, StatusCode

with tracer.start_as_current_span("payment_operation") as span:
    try:
        # Ваш код
        result = await process()
        span.set_status(Status(StatusCode.OK))
        return result
    except Exception as e:
        span.set_status(Status(StatusCode.ERROR, str(e)))
        span.record_exception(e)
        raise
```

---

## 📈 Мониторинг и алерты

### Prometheus Metrics

OpenTelemetry экспортирует метрики:

```python
from opentelemetry import metrics

meter = metrics.get_meter(__name__)
payment_counter = meter.create_counter(
    name="payment.processed",
    description="Number of payments processed",
)

payment_counter.add(1, {"gateway": "yookassa", "status": "success"})
```

### Grafana Dashboard

Импортируйте дашборд для визуализации трассировок.

**Ключевые метрики:**
- Request duration (p50, p95, p99)
- Error rate by endpoint
- Gateway response times
- Database query times

### Алерты

Настройте алерты на:
- High error rate (> 5%)
- High latency (p99 > 1s)
- Service unavailable
- Database connection errors

---

## 🔍 Примеры трассировок

### Payment Flow

```
POST /api/v1/payments/create
├─ authenticate_user (0.5ms)
├─ validate_request (0.2ms)
├─ payment_gateway.create_payment (150ms)
│  ├─ HTTP POST to yookassa (145ms)
│  └─ parse_response (5ms)
├─ save_to_database (10ms)
└─ send_notification (50ms)
   └─ Redis PUBLISH (48ms)
```

### Webhook Processing

```
POST /webhooks/yookassa
├─ verify_signature (0.1ms)
├─ verify_ip_whitelist (0.05ms)
├─ parse_webhook (0.3ms)
├─ update_payment_status (5ms)
│  └─ SQL UPDATE (4.5ms)
└─ celery.send_task (2ms)
   └─ Redis LPUSH (1.8ms)
```

---

## 🛠️ Troubleshooting

### Трассировки не отправляются

1. Проверьте `OPENTELEMETRY_ENABLED=true`
2. Проверьте доступность экспортера
3. Проверьте логи на ошибки инициализации

### Нет данных о Redis/SQL

1. Убедитесь что инструменты установлены
2. Проверьте версии пакетов instrumentation
3. Перезапустите приложение после установки

### Большой overhead

1. Уменьшите sample_rate
2. Отключите трассировку для health endpoints
3. Используйте batch processor

---

## 📚 Дополнительные ресурсы

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Grafana Tempo](https://grafana.com/docs/tempo/)
- [OpenTelemetry Python](https://opentelemetry-python.readthedocs.io/)

---

*Последнее обновление: Mar 2026*
