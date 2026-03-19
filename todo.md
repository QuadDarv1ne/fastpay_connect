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
- [x] **RuStore Pay SDK Integration** - Mar 2026
  - Серверный шлюз: app/payment_gateways/rustore.py
  - Валидация покупок и подписок через RuStore API
  - Обработка webhook уведомлений с проверкой подписи
  - Двухстадийные платежи (confirm/cancel)
  - API endpoints: /api/v1/rustore/*
  - Webhook handler: /api/v1/webhooks/rustore
  - Тесты: tests/test_rustore.py (13 тестов)
  - Переменные окружения в .env_template
- [x] **Multi-Tenant Support** - Mar 2026
  - Tenant модель: app/models/tenant.py
  - TenantRepository: app/repositories/tenant_repository.py
  - TenantMiddleware: app/middleware/tenant.py (X-API-Key header)
  - Tenant context: app/utils/tenant.py
  - Обновлены модели: Payment, User (tenant_id foreign key)
  - Обновлены репозитории: PaymentRepository, UserRepository (tenant filter)
  - API endpoints: /api/v1/tenants/*
  - Тесты: tests/test_multi_tenant.py (18 тестов)
- [x] **Multi-Currency Support** - Mar 2026
  - Currency enum: 10 валют (RUB, USD, EUR, KZT, BYN, CNY, TRY, AED, GBP, JPY)
  - CurrencyService: app/utils/currency.py
  - Конвертация валют через базовую RUB
  - API endpoints: /api/v1/currencies/*
  - Символы валют (₽, $, €, ₸, etc.)
  - Тесты: tests/test_multi_currency.py (28 тестов)

## Pending

### High Priority
- [x] OAuth2 authentication for admin panel
- [x] API versioning (v1/v2)
- [x] Webhook retry queue monitoring dashboard

### Medium Priority
- [x] Pagination for admin endpoints
- [x] GraphQL API support
- [x] WebSocket notifications for payment events
- [x] Multi-tenant support

### Low Priority
- [x] Multi-currency support
- [x] Payment statistics dashboard
- [x] **SBP Integration** - Mar 2026
  - Серверный шлюз: app/payment_gateways/sbp.py
  - Справочник банков: SBPBank (20 банков с BIC кодами)
  - Статусы платежей: SBPStatus (PENDING, PAID, REJECTED, EXPIRED, REFUNDED)
  - HMAC-SHA256 подпись запросов с timestamp verification
  - Создание платежей с QR кодом и payment_url
  - Возврат и отмена платежей
  - Webhook уведомления с проверкой подписи
  - API endpoints: /api/v1/sbp/* (8 endpoints)
  - Webhook handler: /api/v1/webhooks/sbp
  - Валидация и нормализация номеров телефонов
  - Тесты: tests/test_sbp.py (28 тестов)
  - Переменные окружения в .env_template
- [ ] Apple Pay / Google Pay integration
- [ ] Mobile SDK (iOS/Android)
- [ ] Payment analytics and reporting API
- [ ] Multi-language support (i18n)

---

## Project Health & Quality Metrics

### Current State (Mar 2026)
- **Payment Gateways**: 8 (YooKassa, Tinkoff, CloudPayments, UnitPay, RoboKassa, RuStore, SBP)
- **Test Files**: 36
- **API Version**: v1 (v2 planned)
- **Database**: SQLite (dev) / PostgreSQL (prod via Docker)
- **Async Tasks**: Celery + Redis (webhook retry queue)

### Technical Debt
- [x] Add webhook security middleware for IP and header validation
- [ ] Add integration tests for all payment gateways (currently ~60% coverage)
- [ ] Implement API v2 with breaking changes support
- [ ] Add OpenAPI/Swagger documentation for all endpoints
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Add performance benchmarks and load testing
- [ ] Implement distributed tracing (OpenTelemetry)
- [ ] Add comprehensive error codes documentation

### Future Enhancements
- [ ] Recurring payments / subscriptions API
- [ ] Split payments / marketplace support
- [ ] Fraud detection integration
- [ ] Real-time payment notifications (WebSocket)
- [ ] Admin dashboard with analytics
- [ ] Export payment data (CSV, Excel, PDF)
- [ ] Webhook management UI (retry, view history)
