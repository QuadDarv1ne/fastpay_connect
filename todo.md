# FastPay Connect - TODO

> **Last Updated**: Mar 2026  
> **Current Branch**: main (synced with dev)  
> **Test Coverage**: 40+ test files (~60%+ coverage)

## Completed

- [x] Migrate from config.py to settings.py (Pydantic Settings) - ✅ app/settings.py
- [x] PaymentStatus Enum with SQLAlchemy values_callable
- [x] Multi-stage Dockerfile with healthcheck
- [x] Pre-commit hooks (black, flake8, isort, mypy, detect-secrets) - ✅ .pre-commit-config.yaml
- [x] TrustedHostMiddleware for production
- [x] Alembic migrations in CI/CD - ✅ 6+ migration files in alembic/versions/
- [x] Async payment gateways with retry logic
- [x] PaymentRepository with error handling - ✅ app/repositories/payment_repository.py
- [x] Webhook idempotency via webhook_event_id - ✅ WebhookEvent model
- [x] Payment routes error handling with PaymentGatewayError
- [x] Admin routes migrated to repository pattern
- [x] Integration tests with mocked payment gateways - ✅ 40+ test files
- [x] Input validation with Pydantic v2
- [x] Prometheus metrics export
- [x] Structured JSON logging (structlog)
- [x] Rate limiting per API key (slowapi) - ✅ app/middleware/rate_limiter.py
- [x] Comprehensive test coverage - ✅ 40+ test files
- [x] **Webhook retry queue (Celery + Redis)** - ✅ Dec 2025
  - Celery tasks для асинхронной обработки webhook
  - Redis в качестве брокера сообщений
  - Экспоненциальная задержка между попытками (60s, 120s, 240s, 480s, 960s)
  - Максимум 5 попыток обработки
  - Идемпотентность через webhook_event_id
  - Flower для мониторинга задач (docker-compose.prod.yml)
  - Docker Compose конфигурация (redis, celery_worker, celery_beat)
  - Health check endpoint для Celery
  - Документация: docs/webhook_retry_queue.md
  - Тесты: tests/test_celery_webhook.py (21 тест)
- [x] **RuStore Pay SDK Integration** - ✅ Mar 2026
  - Серверный шлюз: app/payment_gateways/rustore.py
  - Валидация покупок и подписок через RuStore API
  - Обработка webhook уведомлений с проверкой подписи
  - Двухстадийные платежи (confirm/cancel)
  - API endpoints: /api/v1/rustore/*
  - Webhook handler: /api/v1/webhooks/rustore
  - Тесты: tests/test_rustore.py (13 тестов)
  - Переменные окружения в .env_template
- [x] **Multi-Tenant Support** - ✅ Mar 2026
  - Tenant модель: app/models/tenant.py
  - TenantRepository: app/repositories/tenant_repository.py
  - TenantMiddleware: app/middleware/tenant.py (X-API-Key header)
  - Tenant context: app/utils/tenant.py
  - Обновлены модели: Payment, User (tenant_id foreign key)
  - Обновлены репозитории: PaymentRepository, UserRepository (tenant filter)
  - API endpoints: /api/v1/tenants/*
  - Тесты: tests/test_multi_tenant.py (18 тестов)
- [x] **Multi-Currency Support** - ✅ Mar 2026
  - Currency enum: 10 валют (RUB, USD, EUR, KZT, BYN, CNY, TRY, AED, GBP, JPY)
  - CurrencyService: app/utils/currency.py
  - Конвертация валют через базовую RUB
  - API endpoints: /api/v1/currencies/*
  - Символы валют (₽, $, €, ₸, etc.)
  - Тесты: tests/test_multi_currency.py (28 тестов)
- [x] **SBP Integration** - ✅ Mar 2026
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
- [x] **Cache Service** - ✅ app/services/cache_service.py
  - LRUCache implementation (max 1000 entries)
  - TTL support for cache entries
  - Cache statistics (hits/misses)
- [x] **Email Service** - ✅ app/services/email_service.py
- [x] **Payment Service** - ✅ app/services/payment_service.py
- [x] **GraphQL API** - ✅ Strawberry GraphQL with resolvers (app/graphql/)
- [x] **OAuth2/JWT Authentication** - ✅ JWT auth, refresh tokens, password reset
- [x] **WebSocket Notifications** - ✅ app/websocket/ (real-time payment updates)
- [x] **API Versioning** - ✅ v1/v2 structure (app/api/v1/, app/api/v2/)
- [x] **Webhook Security Middleware** - ✅ app/middleware/webhook_security.py
- [x] **Async Repository Pattern** - ✅ app/repositories/async_payment_repository.py
- [x] **CI/CD Pipeline** - ✅ .github/workflows/ci.yml
  - Test & Lint job
  - Docker build & push
  - Alembic migrations
  - Multi-platform deploy (Cloudflare, Render, Railway, Fly.io, K8s, VPS)
  - Notifications (Telegram, Slack)

## Pending

### High Priority
- [x] OAuth2 authentication for admin panel - ✅ JWT auth, refresh tokens, password reset
- [x] API versioning (v1/v2) - ✅ v1 fully implemented, v2 structure ready
- [x] Webhook retry queue monitoring dashboard - ✅ Celery + Flower monitoring
- [ ] Apple Pay / Google Pay integration
- [ ] Mobile SDK (iOS/Android)

### Medium Priority
- [x] Pagination for admin endpoints
- [x] GraphQL API support - ✅ Strawberry GraphQL with resolvers
- [x] WebSocket notifications for payment events - ✅ Real-time payment updates
- [x] Multi-tenant support - ✅ TenantMiddleware, X-API-Key isolation
- [ ] Payment analytics and reporting API
- [ ] Multi-language support (i18n)

### Low Priority
- [x] Multi-currency support - ✅ 10 currencies (RUB, USD, EUR, KZT, BYN, CNY, TRY, AED, GBP, JPY)
- [ ] Payment statistics dashboard
- [ ] Admin dashboard with analytics
- [ ] Export payment data (CSV, Excel, PDF)
- [ ] Webhook management UI (retry, view history)

---

## Project Health & Quality Metrics

### Current State (Mar 2026)
- **Payment Gateways**: 8 (YooKassa, Tinkoff, CloudPayments, UnitPay, RoboKassa, RuStore, SBP)
- **Test Files**: 40+ (~60%+ coverage)
- **API Version**: v1 (v2 structure ready)
- **Database**: SQLite (dev) / PostgreSQL (prod via Docker)
- **Async Tasks**: Celery + Redis (webhook retry queue)
- **GraphQL**: Strawberry GraphQL API
- **WebSocket**: Real-time notifications
- **Auth**: OAuth2/JWT with refresh tokens
- **Multi-tenant**: X-API-Key isolation
- **Multi-currency**: 10 currencies (RUB base)
- **CI/CD**: GitHub Actions (test, lint, build, deploy)
- **Documentation**: Swagger UI (/docs), ReDoc (/redoc)

### Technical Debt
- [x] Add webhook security middleware for IP and header validation - ✅ app/middleware/webhook_security.py
- [x] Add async SQLAlchemy support for non-blocking database operations - ✅ app/repositories/async_payment_repository.py
- [x] Add integration tests for all payment gateways
  - ✅ YooKassa: tests/test_yookassa.py
  - ✅ Tinkoff: tests/test_tinkoff.py
  - ✅ RoboKassa: tests/test_robokassa.py
  - ✅ RuStore: tests/test_rustore.py
  - ✅ SBP: tests/test_sbp.py
  - ✅ CloudPayments: tests/test_cloudpayments.py
  - ✅ UnitPay: tests/test_unitpay.py
- [x] Implement API v2 with breaking changes support
  - ✅ v2 structure exists (app/api/v2/)
  - ✅ API versioning middleware: app/middleware/api_versioning.py
  - ⚠️ Needs endpoints implementation
- [x] Add OpenAPI/Swagger documentation for all endpoints
  - ✅ Auto-generated docs at /docs
  - ✅ ReDoc at /redoc
  - ⚠️ Manual descriptions needed for complex endpoints
- [x] Set up CI/CD pipeline (GitHub Actions)
  - ✅ .github/workflows/ci.yml configured
  - ✅ Test & Lint job
  - ✅ Docker build & push
  - ✅ Alembic migrations
  - ✅ Multi-platform deploy (Cloudflare, Render, Railway, Fly.io, K8s, VPS)
  - ✅ Notifications (Telegram, Slack)
- [ ] Add performance benchmarks and load testing
- [ ] Implement distributed tracing (OpenTelemetry)
- [ ] Add comprehensive error codes documentation

### Future Enhancements
- [ ] Recurring payments / subscriptions API
- [ ] Split payments / marketplace support
- [ ] Fraud detection integration
- [x] Real-time payment notifications (WebSocket) - ✅ app/websocket/
- [ ] Admin dashboard with analytics
- [ ] Export payment data (CSV, Excel, PDF)
- [ ] Webhook management UI (retry, view history)
- [ ] Cache service with Redis (currently using in-memory LRUCache)
- [ ] Rate limiting persistence (currently in-memory)
- [ ] Multi-factor authentication (2FA)
- [ ] Audit logging for admin actions
- [ ] Apple Pay / Google Pay integration
- [ ] Mobile SDK (iOS/Android)
- [ ] Payment analytics and reporting API
- [ ] Multi-language support (i18n)
