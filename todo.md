# FastPay Connect - TODO

> **Last Updated**: Mar 2026  
> **Current Branch**: main & dev (synced)  
> **Test Coverage**: 40 test files (~60%+ coverage)  
> **Payment Gateways**: 8 integrated  
> **CI/CD**: GitHub Actions (multi-platform deploy)  
> **Codebase**: 79 Python files (app/)

## Completed

### Core Infrastructure
- [x] Migrate from config.py to settings.py (Pydantic Settings) - ✅ app/settings.py
- [x] PaymentStatus Enum with SQLAlchemy values_callable
- [x] Multi-stage Dockerfile with healthcheck
- [x] Pre-commit hooks (black, flake8, isort, mypy, detect-secrets) - ✅ .pre-commit-config.yaml
- [x] TrustedHostMiddleware for production
- [x] Alembic migrations - ✅ 5 migration files in alembic/versions/
- [x] Async payment gateways with retry logic
- [x] Input validation with Pydantic v2
- [x] Structured JSON logging (structlog)
- [x] Environment settings validation - ✅ app/settings.py (Pydantic Settings)
- [x] Settings validator - ✅ app/utils/settings_validator.py

### Repositories & Data Layer
- [x] PaymentRepository with error handling - ✅ app/repositories/payment_repository.py
- [x] AsyncRepository pattern - ✅ app/repositories/async_payment_repository.py
- [x] TenantRepository - ✅ app/repositories/tenant_repository.py
- [x] UserRepository - ✅ app/repositories/user_repository.py
- [x] WebhookEventRepository - ✅ app/repositories/webhook_event_repository.py
- [x] Webhook idempotency via webhook_event_id - ✅ WebhookEvent model

### Payment Gateways (8 total)
- [x] YooKassa - ✅ app/payment_gateways/yookassa.py + tests/test_yookassa.py
- [x] Tinkoff - ✅ app/payment_gateways/tinkoff.py + tests/test_tinkoff.py
- [x] CloudPayments - ✅ app/payment_gateways/cloudpayments.py + tests/test_cloudpayments.py
- [x] UnitPay - ✅ app/payment_gateways/unitpay.py + tests/test_unitpay.py
- [x] RoboKassa - ✅ app/payment_gateways/robokassa.py + tests/test_robokassa.py
- [x] RuStore - ✅ app/payment_gateways/rustore.py + tests/test_rustore.py (13 тестов)
- [x] SBP - ✅ app/payment_gateways/sbp.py + tests/test_sbp.py (28 тестов)

### Features
- [x] **Webhook retry queue (Celery + Redis)** - ✅ Dec 2025
  - Celery tasks: app/tasks/webhook_tasks.py (5 задач)
  - Redis в качестве брокера сообщений
  - Экспоненциальная задержка между попытками (60s, 120s, 240s, 480s, 960s)
  - Максимум 5 попыток обработки
  - Идемпотентность через webhook_event_id
  - Flower для мониторинга задач (docker-compose.prod.yml)
  - Docker Compose конфигурация (redis, celery_worker, celery_beat)
  - Health check endpoint: /health/celery
  - Документация: docs/webhook_retry_queue.md (309 строк)
  - Тесты: tests/test_celery_webhook.py (21 тест)
- [x] **RuStore Pay SDK Integration** - ✅ Mar 2026
- [x] **Multi-Tenant Support** - ✅ Mar 2026
  - TenantMiddleware: app/middleware/tenant.py (X-API-Key header)
  - Tenant context: app/utils/tenant.py
  - Тесты: tests/test_multi_tenant.py (18 тестов)
- [x] **Multi-Currency Support** - ✅ Mar 2026
  - Currency enum: 10 валют (RUB, USD, EUR, KZT, BYN, CNY, TRY, AED, GBP, JPY)
  - CurrencyService: app/utils/currency.py
  - Тесты: tests/test_multi_currency.py (28 тестов)
- [x] **SBP Integration** - ✅ Mar 2026
  - HMAC-SHA256 подпись запросов с timestamp verification
  - Справочник банков: SBPBank (20 банков с BIC кодами)
  - API endpoints: /api/v1/sbp/* (8 endpoints)
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
- [x] **Rate limiting per API key** - ✅ app/middleware/rate_limiter.py (slowapi)
- [x] **IP Validator** - ✅ app/utils/ip_validator.py
- [x] **Metrics utility** - ✅ app/utils/metrics.py

### Testing & CI/CD
- [x] Integration tests with mocked payment gateways - ✅ 40 test files
- [x] CI/CD Pipeline - ✅ .github/workflows/ci.yml
  - Test & Lint job
  - Docker build & push (ghcr.io)
  - Alembic migrations
  - Multi-platform deploy (Cloudflare, Render, Railway, Fly.io, K8s, VPS)
  - Notifications (Telegram, Slack)
- [x] Prometheus metrics export - ✅ app/utils/metrics.py
- [x] Health check endpoints - ✅ /health, /health/celery, /health/db, /health/redis
- [x] pytest.ini configured - ✅ pytest.ini
- [x] conftest.py with fixtures - ✅ tests/conftest.py

### Utilities & Helpers
- [x] Currency utils - ✅ app/utils/currency.py
- [x] Security utils (JWT, hashing) - ✅ app/utils/security.py
- [x] Logger utils - ✅ app/utils/logger.py
- [x] Helpers - ✅ app/utils/helpers.py
- [x] Tenant utils - ✅ app/utils/tenant.py
- [x] IP Validator - ✅ app/utils/ip_validator.py
- [x] Metrics - ✅ app/utils/metrics.py
- [x] Settings validator - ✅ app/utils/settings_validator.py

### Documentation
- [x] Swagger UI (/docs), ReDoc (/redoc)
- [x] docs/webhook_retry_queue.md (309 строк)
- [x] docs/webhook_monitoring_dashboard.md (360 строк)
- [x] docs/websocket_notifications.md
- [x] docs/oauth2_authentication.md
- [x] docs/api_versioning.md
- [x] docs/DEPLOYMENT.md
- [x] docs/CLOUDFLARE_DEPLOY.md

## Pending

### High Priority
- [ ] API v2 endpoints implementation (structure ready: app/api/v2/)
- [ ] Apple Pay / Google Pay integration
- [ ] Mobile SDK (iOS/Android)
- [ ] Performance benchmarks and load testing

### Medium Priority
- [ ] Payment analytics and reporting API
- [ ] Multi-language support (i18n)
- [ ] Cache service with Redis (currently using in-memory LRUCache)
- [ ] Rate limiting persistence (currently in-memory)
- [ ] Distributed tracing (OpenTelemetry)

### Low Priority
- [ ] Payment statistics dashboard (basic dashboard exists: routes/dashboard_routes.py)
- [ ] Admin dashboard with analytics
- [ ] Export payment data (CSV, Excel, PDF)
- [ ] Webhook management UI (retry, view history)
- [ ] Multi-factor authentication (2FA)
- [ ] Audit logging for admin actions
- [ ] Comprehensive error codes documentation

---

## Project Health & Quality Metrics

### Current State (Mar 2026)
| Metric | Value |
|--------|-------|
| **Payment Gateways** | 8 (YooKassa, Tinkoff, CloudPayments, UnitPay, RoboKassa, RuStore, SBP) |
| **Test Files** | 40 files (~60%+ coverage) |
| **API Version** | v1 (stable), v2 (structure ready) |
| **Database** | SQLite (dev) / PostgreSQL (prod via Docker) |
| **Async Tasks** | Celery + Redis (webhook retry queue) |
| **GraphQL** | Strawberry GraphQL API |
| **WebSocket** | Real-time notifications |
| **Auth** | OAuth2/JWT with refresh tokens |
| **Multi-tenant** | X-API-Key isolation |
| **Multi-currency** | 10 currencies (RUB base) |
| **CI/CD** | GitHub Actions (test, lint, build, deploy) |
| **Deploy Targets** | Cloudflare, Render, Railway, Fly.io, K8s, VPS |
| **Documentation** | Swagger UI (/docs), ReDoc (/redoc), 7 docs |

### Technical Debt
- [x] Webhook security middleware - ✅ app/middleware/webhook_security.py
- [x] Async SQLAlchemy support - ✅ app/repositories/async_payment_repository.py
- [x] Integration tests for all payment gateways
  - ✅ YooKassa, Tinkoff, RoboKassa, RuStore, SBP, CloudPayments, UnitPay
- [x] API v2 structure - ✅ app/api/v2/ + middleware/api_versioning.py
- [x] OpenAPI/Swagger documentation - ✅ /docs, /redoc
- [x] CI/CD pipeline - ✅ .github/workflows/ci.yml
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Comprehensive error codes documentation
- [ ] API v2 endpoints implementation

### Future Enhancements
- [ ] Recurring payments / subscriptions API
- [ ] Split payments / marketplace support
- [ ] Fraud detection integration
- [ ] Apple Pay / Google Pay integration
- [ ] Mobile SDK (iOS/Android)
- [ ] Payment analytics and reporting API
- [ ] Multi-language support (i18n)
