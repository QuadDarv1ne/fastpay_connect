# FastPay Connect - TODO

## Критичные (High Priority)

- [ ] Добавить интеграционные тесты с httpx.AsyncClient (mock платёжных шлюзов)
- [ ] Добавить обработку исключений PaymentGatewayError в payment_routes.py
- [ ] Добавить retry logic для webhook обработки
- [ ] Добавить валидацию webhook payload схемой

## Важные (Medium Priority)

- [ ] Добавить кэширование для get_statistics (Redis/TTL)
- [ ] Добавить пагинацию для admin endpoints
- [ ] Добавить экспорт метрик Prometheus
- [ ] Добавить структурированное логирование (json format)
- [ ] Добавить background task для отправки email уведомлений

## Желательные (Low Priority)

- [ ] Добавить поддержку multi-currency (не только RUB)
- [ ] Добавить webhook retry queue (Celery + Redis)
- [ ] Добавить dashboard со статистикой платежей
- [ ] Добавить rate limiting per API key
- [ ] Добавить поддержку дополнительных платёжных систем

## Технические долги

- [ ] Убрать дублирование кода в payment gateway implementations
- [ ] Добавить factory pattern для создания gateway instances
- [ ] Мигрировать на SQLAlchemy 2.0 style queries
- [ ] Добавить OpenTelemetry tracing
