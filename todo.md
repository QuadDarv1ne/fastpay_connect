# FastPay Connect - TODO

## Completed

- [x] Migrate from config.py to settings.py (Pydantic Settings)
- [x] PaymentStatus Enum with SQLAlchemy values_callable
- [x] Multi-stage Dockerfile with healthcheck
- [x] Pre-commit hooks (black, flake8, isort, mypy, detect-secrets)
- [x] TrustedHostMiddleware for production
- [x] Alembic migrations in CI/CD
- [x] Async payment gateways with retry logic
- [x] PaymentRepository with error handling
- [x] Webhook idempotency via webhook_event_id
- [x] Payment routes error handling with PaymentGatewayError
- [x] Admin routes migrated to repository pattern
- [x] Integration tests with mocked payment gateways
- [x] Input validation with Pydantic v2
- [x] Prometheus metrics export
- [x] Structured JSON logging (structlog)
- [x] Rate limiting per API key (slowapi)
- [x] Comprehensive test coverage (23+ test files)
- [x] **Webhook retry queue (Celery + Redis)** - Dec 2026
  - Celery tasks для асинхронной обработки webhook
  - Redis в качестве брокера сообщений
  - Экспоненциальная задержка между попытками (60s, 120s, 240s, 480s, 960s)
  - Максимум 5 попыток обработки
  - Идемпотентность через webhook_event_id
  - Flower для мониторинга задач
  - Docker Compose конфигурация (redis, celery_worker, celery_beat)
  - Health check endpoint для Celery
  - Документация: docs/webhook_retry_queue.md
  - Тесты: tests/test_celery_webhook.py (21 тест)

## Pending

### High Priority
- [x] OAuth2 authentication for admin panel
- [x] API versioning (v1/v2)
- [x] Webhook retry queue monitoring dashboard

### Medium Priority
- [x] Pagination for admin endpoints
- [x] GraphQL API support
- [x] WebSocket notifications for payment events
- [ ] Multi-tenant support

### Low Priority
- [ ] Multi-currency support
- [x] Payment statistics dashboard
- [ ] Additional payment systems (SBP, Apple Pay, Google Pay)
- [ ] Mobile SDK (iOS/Android)
