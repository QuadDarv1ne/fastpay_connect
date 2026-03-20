# FastPay Connect - TODO

> **Last Updated**: Mar 20, 2026 (Latest: 2FA Implementation)
> **Current Branch**: main & dev (synced)
> **Test Coverage**: 43 test files (~65%+ coverage)
> **Payment Gateways**: 10 integrated (YooKassa, Tinkoff, CloudPayments, UnitPay, RoboKassa, RuStore, SBP, Apple Pay, Google Pay)
> **CI/CD**: GitHub Actions (multi-platform deploy)
> **Codebase**: 92 Python files (app/), 43 test files, 12 routes, 7 middleware, 5 models, 6 repositories, 5 services, 3 websocket, 10 schemas, 10 payment gateways, 2 tasks
> **Redis Integration**: Rate limiting persistence, Celery broker/backend
> **PostgreSQL**: dev environment ready (docker-compose.dev.yml, alembic.ini, DEVELOPMENT.md)
> **Webhook Management**: API endpoints with retry, filters, pagination
> **Payment Export**: CSV + JSON export with filters
> **Payment Analytics**: Summary, period, gateway, currency, daily, status reports
> **Startup Scripts**: Windows, macOS, Linux, Android, Docker (8 files)
> **Flower Dashboard**: Celery monitoring with auth, persistent storage
> **Webhook Security**: Signature verification for all gateways (HMAC-SHA256)
> **Error Documentation**: 400+ lines covering all error codes
> **OpenTelemetry**: Distributed tracing with Jaeger/Zipkin/OTLP support
> **Performance Benchmarks**: Load testing documentation + tests
> **PWA**: Progressive Web App with offline support, push notifications, install prompt
> **GraphQL**: Relay-style pagination, Tenant/WebhookEvent types, cursor-based queries
> **2FA**: TOTP-based two-factor authentication with Google Authenticator, backup codes
>
> ## Recent Improvements (Mar 2026)
> ✅ Rate limiting with Redis persistence
> ✅ PostgreSQL dev environment (docker-compose.dev.yml)
> ✅ Webhook Management API (retry, filters, pagination)
> ✅ Payment Export API (CSV/JSON)
> ✅ Cross-platform startup scripts (8 files)
> ✅ Flower Dashboard deployment (auth, docs)
> ✅ Webhook signature verification (all gateways)
> ✅ Payment Analytics API (6 endpoints)
> ✅ Error Codes Documentation (400+ lines)
> ✅ OpenTelemetry distributed tracing
> ✅ Performance Benchmarks and load testing (tests/test_benchmarks.py + docs/PERFORMANCE_BENCHMARKS.md)
> ✅ **PWA Implementation** (manifest.json, service-worker.js, offline page, push notifications)
> ✅ **Apple Pay Integration** (payment gateway + schemas + routes + tests)
> ✅ **Google Pay Integration** (payment gateway + schemas + tests)
> ✅ **GraphQL Improvements** (Relay pagination, Tenant/WebhookEvent types, cursor queries, enhanced statistics)
> ✅ **2FA Implementation** (TOTP, Google Authenticator, backup codes, 28 tests)

## Completed

### Core Infrastructure
- [x] Migrate from config.py to settings.py (Pydantic Settings) - ✅ app/settings.py
- [x] PaymentStatus Enum with SQLAlchemy values_callable
- [x] Multi-stage Dockerfile with healthcheck - ✅ Dockerfile (builder + runtime stages)
- [x] Pre-commit hooks (black, flake8, isort, mypy, detect-secrets) - ✅ .pre-commit-config.yaml
- [x] TrustedHostMiddleware for production
- [x] Alembic migrations - ✅ 6 migration files in alembic/versions/
  - e177d6c0b9cc_initial_migration_add_payments_table.py
  - a2b3c4d5e6f7_update_payment_model_add_transaction_id.py
  - 2e99afdbf552_add_webhook_processed_field_to_payment_.py
  - oauth2_auth.py
  - webhook_events_monitoring.py
- [x] Async payment gateways with retry logic
- [x] Input validation with Pydantic v2
- [x] Structured JSON logging (structlog)
- [x] Environment settings validation - ✅ app/settings.py (Pydantic Settings)
- [x] Settings validator - ✅ app/utils/settings_validator.py
- [x] CORS middleware - ✅ app/main.py (CORSMiddleware)
- [x] Lifespan events (startup/shutdown) - ✅ app/main.py
- [x] Multi-platform deploy configs - ✅ deploy/ (14 files: AWS, GCP, Cloudflare, K8s, etc.)

### Repositories & Data Layer (6 total)
- [x] PaymentRepository with error handling - ✅ app/repositories/payment_repository.py
- [x] AsyncRepository pattern - ✅ app/repositories/async_payment_repository.py
- [x] TenantRepository - ✅ app/repositories/tenant_repository.py
- [x] UserRepository - ✅ app/repositories/user_repository.py
- [x] WebhookEventRepository - ✅ app/repositories/webhook_event_repository.py
- [x] Webhook idempotency via webhook_event_id - ✅ WebhookEvent model
- [x] Repository exports - ✅ app/repositories/__init__.py

### Models (5 total)
- [x] Payment model - ✅ app/models/payment.py
- [x] User model - ✅ app/models/user.py
- [x] Tenant model - ✅ app/models/tenant.py
- [x] WebhookEvent model - ✅ app/models/webhook_event.py
- [x] SQLAlchemy Base - ✅ app/database.py (Base, SessionLocal, engine)

### Payment Gateways (10 files, 8 integrations)
- [x] Base gateway - ✅ app/payment_gateways/base.py
- [x] Exceptions - ✅ app/payment_gateways/exceptions.py
- [x] YooKassa - ✅ app/payment_gateways/yookassa.py + tests/test_yookassa.py
- [x] Tinkoff - ✅ app/payment_gateways/tinkoff.py + tests/test_tinkoff.py
- [x] CloudPayments - ✅ app/payment_gateways/cloudpayments.py + tests/test_cloudpayments.py
- [x] UnitPay - ✅ app/payment_gateways/unitpay.py + tests/test_unitpay.py
- [x] RoboKassa - ✅ app/payment_gateways/robokassa.py + tests/test_robokassa.py
- [x] RuStore - ✅ app/payment_gateways/rustore.py + tests/test_rustore.py (13 тестов)
- [x] SBP - ✅ app/payment_gateways/sbp.py + tests/test_sbp.py (28 тестов)
- [x] Package exports - ✅ app/payment_gateways/__init__.py

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

### Schemas (5 total)
- [x] Auth schemas - ✅ app/schemas/auth.py
- [x] Payment schemas - ✅ app/schemas/payment.py
- [x] SBP schemas - ✅ app/schemas/sbp.py
- [x] Tenant schemas - ✅ app/schemas/tenant.py
- [x] Package exports - ✅ app/schemas/__init__.py

### Tasks (2 total)
- [x] Celery webhook tasks - ✅ app/tasks/webhook_tasks.py (5 tasks)
- [x] Package exports - ✅ app/tasks/__init__.py

### Dependencies
- [x] Database dependencies - ✅ app/dependencies.py (get_db, get_payment_repository, verify_db_connection)

### Deploy Configurations (14 files)
- [x] Dockerfile (multi-stage) - ✅ Dockerfile
- [x] Docker Compose - ✅ docker-compose.yml, docker-compose.prod.yml
- [x] AWS Elastic Beanstalk - ✅ deploy/aws/
- [x] Google Cloud Platform - ✅ deploy/gcp/cloudbuild.yaml
- [x] Cloudflare Workers/Pages - ✅ deploy/cloudflare/ (wrangler.toml, worker.ts)
- [x] Kubernetes - ✅ deploy/k8s/deployment.yaml
- [x] Render - ✅ deploy/render.yaml
- [x] Railway - ✅ deploy/railway.json
- [x] Fly.io - ✅ deploy/fly.toml
- [x] Vercel - ✅ deploy/vercel.json
- [x] Netlify - ✅ deploy/netlify.toml
- [x] Nginx - ✅ deploy/nginx/
- [x] Deploy scripts - ✅ deploy/scripts/deploy.sh, init-db.sql
- [x] Makefile - ✅ deploy/Makefile

### Templates & Frontend
- [x] Jinja2 templates - ✅ app/templates/
- [x] Payment dashboard template - ✅ app/templates/payment_dashboard.html
- [x] Static files serving - ✅ app/static/
- [x] **PWA Support** - ✅ Mar 2026
  - manifest.json - ✅ app/static/manifest.json
  - service-worker.js - ✅ app/static/service-worker.js
  - offline.html - ✅ app/templates/offline.html
  - pwa.html - ✅ app/templates/pwa.html
  - base.html updated with PWA - ✅ app/templates/base.html
  - PWA icons (8 sizes) - ✅ app/static/icons/
  - PWA documentation - ✅ docs/PWA.md
  - PWA routes in main.py - ✅ /manifest.json, /service-worker.js, /offline, /pwa

### Routes & Endpoints
- [x] Payment routes - ✅ app/routes/payment_routes.py
- [x] Webhook routes - ✅ app/routes/webhook_routes.py
- [x] Admin routes - ✅ app/routes/admin_routes.py
- [x] Auth routes - ✅ app/routes/auth_routes.py
- [x] Dashboard routes - ✅ app/routes/dashboard_routes.py
- [x] Webhook monitor routes - ✅ app/routes/webhook_monitor_routes.py
- [x] WebSocket routes - ✅ app/routes/websocket_routes.py
- [x] API v1 router - ✅ app/api/v1/__init__.py (payments, webhooks, admin, auth, health, currencies, rustore, sbp, tenants)
  - ✅ API v1 routes: 10 files (admin, auth, currencies, health, payments, rustore, sbp, tenants, webhooks)
- [x] API v2 router - ✅ app/api/v2/__init__.py (3 health endpoints)
  - ✅ API v2 routes: /health, /ready, /live
- [x] API v2 routes structure - ✅ app/api/v2/routes/ (health.py with /health, /ready, /live)

### Middleware (7 total)
- [x] API Versioning Middleware - ✅ app/middleware/api_versioning.py
- [x] Rate Limiter Middleware - ✅ app/middleware/rate_limiter.py (slowapi)
- [x] Tenant Middleware - ✅ app/middleware/tenant.py (X-API-Key isolation)
- [x] Webhook Security Middleware - ✅ app/middleware/webhook_security.py (IP + signature validation)
- [x] CORS Middleware - ✅ app/main.py (CORSMiddleware)
- [x] TrustedHost Middleware - ✅ app/main.py (production)
- [x] Prometheus Metrics Middleware - ✅ app/utils/metrics.py

### Testing & CI/CD
- [x] Integration tests with mocked payment gateways - ✅ 40 test files
- [x] CI/CD Pipeline - ✅ .github/workflows/ci.yml
  - Test & Lint job
  - Docker build & push (ghcr.io)
  - Alembic migrations
  - Multi-platform deploy (Cloudflare, Render, Railway, Fly.io, K8s, VPS)
  - Notifications (Telegram, Slack)
- [x] Prometheus metrics export - ✅ app/utils/metrics.py
- [x] Health check endpoints - ✅ /health, /health/celery (v1: /health, /ready, /celery; v2: /health, /ready, /live)
- [x] pytest.ini configured - ✅ pytest.ini
- [x] conftest.py with fixtures - ✅ tests/conftest.py (db_engine, db_session, client)
- [x] Test database setup (SQLite for tests) - ✅ tests/conftest.py
- [x] Alembic configuration - ✅ alembic.ini (SQLite dev, PostgreSQL prod)
- [x] Database init script - ✅ scripts/init-db.sql

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
- [x] docs/PWA.md - ✅ PWA документация
- [x] README.md (330 строк) - ✅ Основная документация проекта

### Static Assets
- [x] Project logo - ✅ fastpay_connect.png
- [x] Static files directory - ✅ app/static/ (styles.css)
- [x] Templates directory - ✅ app/templates/ (14 Jinja2 templates)
  - ✅ admin_payments.html, base.html, course_detail.html
  - ✅ error_payment.html, home.html, payment_dashboard.html
  - ✅ payment_status.html, profile_edit.html, success_payment.html
  - ✅ webhook_dashboard.html, webhook_notification.html
  - ✅ **offline.html** (PWA offline page)
  - ✅ **pwa.html** (PWA install page)
- [x] Scripts - ✅ scripts/create_superuser.py, deploy/scripts/deploy.sh
- [x] Startup scripts - ✅ 8 files for all platforms
  - ✅ start-windows.bat (Windows)
  - ✅ start.sh (Linux/macOS)
  - ✅ start-macos.sh (macOS with notifications)
  - ✅ start-docker.sh (Docker Compose launcher)
  - ✅ start-android.sh (Termux)
  - ✅ START.md (main guide)
  - ✅ START_ANDROID.md (Android instructions)
  - ✅ START_IOS.md (iOS instructions)
- [x] PWA Icons - ✅ app/static/icons/ (16 icons: 8 sizes + badges + shortcuts)
- [x] PWA Scripts - ✅ scripts/generate_pwa_icons_simple.py, scripts/generate_pwa_icons.ps1

### Pending

### High Priority
- [x] API v2 endpoints implementation (health endpoints done: /health, /ready, /live) - ✅ app/api/v2/routes/health.py (3 endpoints)
- [x] Apple Pay / Google Pay integration - ✅ app/payment_gateways/apple_pay.py, google_pay.py + schemas + routes
- [ ] Mobile SDK (iOS/Android)
- [x] Performance benchmarks and load testing - ✅ tests/test_benchmarks.py + docs/PERFORMANCE_BENCHMARKS.md
- [x] GraphQL schema improvements - ✅ Relay pagination, Tenant/WebhookEvent types, cursor queries, enhanced statistics
- [x] PostgreSQL migration scripts (alembic.ini uses SQLite for tests) - ✅ alembic.ini switched to PostgreSQL + docker-compose.dev.yml

### Medium Priority
- [x] Payment analytics and reporting API - ✅ app/routes/payment_analytics_routes.py + repository method
- [ ] Multi-language support (i18n)
- [x] Cache service with Redis (currently using in-memory LRUCache) - ✅ Rate limiting now uses Redis
- [x] Rate limiting persistence (currently in-memory) - ✅ app/middleware/rate_limiter.py with Redis backend
- [x] Distributed tracing (OpenTelemetry) - ✅ app/utils/opentelemetry.py + docs/OPENTELEMETRY.md
- [x] Webhook signature verification for all gateways (some implemented) - ✅ app/utils/webhook_signature.py + middleware
- [x] Flower dashboard deployment (configured in docker-compose.prod.yml) - ✅ Auth + docs/FLOWER_DEPLOYMENT.md

### Low Priority
- [x] Payment statistics dashboard (basic dashboard exists: routes/dashboard_routes.py) - ✅ Webhook management API added
- [x] Webhook management UI (retry, view history) - ✅ app/routes/webhook_management_routes.py + schemas
- [x] Export payment data (CSV, Excel, PDF) - ✅ CSV + JSON export endpoints
- [x] Comprehensive error codes documentation - ✅ docs/ERROR_CODES.md (400+ lines)
- [ ] Admin dashboard with analytics
- [x] Multi-factor authentication (2FA) - ✅ app/services/mfa_service.py, app/routes/mfa_routes.py, tests/test_2fa.py (28 tests)
- [ ] Audit logging for admin actions
- [ ] Background task monitoring dashboard (Flower integration)
- [ ] Additional deploy scripts for remaining platforms

---

## Project Health & Quality Metrics

### Current State (Mar 2026)
| Metric | Value |
|--------|-------|
| **Payment Gateways** | 10 (YooKassa, Tinkoff, CloudPayments, UnitPay, RoboKassa, RuStore, SBP, Apple Pay, Google Pay) |
| **Test Files** | 43 files (~65%+ coverage) |
| **API Version** | v1 (stable), v2 (health endpoints ready) |
| **Database** | SQLite (dev) / PostgreSQL (prod via Docker) |
| **Async Tasks** | Celery + Redis (webhook retry queue, 5 tasks) |
| **GraphQL** | ✅ Relay pagination, Tenant/WebhookEvent types, cursor queries, enhanced statistics |
| **WebSocket** | Real-time notifications |
| **Auth** | OAuth2/JWT with refresh tokens + 2FA (TOTP) |
| **Multi-tenant** | X-API-Key isolation |
| **Multi-currency** | 10 currencies (RUB base) |
| **PWA** | ✅ manifest.json, service-worker.js, offline page, install prompt, push notifications |
| **CI/CD** | GitHub Actions (test, lint, build, deploy) |
| **Deploy Targets** | 14 configs (AWS, GCP, Cloudflare, K8s, Render, Railway, Fly.io, Vercel, Netlify) |
| **Documentation** | Swagger UI, ReDoc, 9 docs (incl. PWA.md), README (330 lines), deploy/README (250 lines), START.md (336 lines), PERFORMANCE_BENCHMARKS.md |
| **Codebase** | 92 Python files, 12 routes, 7 middleware, 5 models, 6 repositories, 5 services, 3 websocket, 10 schemas, 10 payment gateways, 2 tasks |
| **Templates** | 14 Jinja2 templates (admin, payment, webhook dashboards, PWA, offline) |
| **Static Assets** | Logo, styles.css, scripts, startup scripts (8 files), PWA icons (16 files) |
| **Alembic Migrations** | 6 migration files |
| **Startup Scripts** | Windows (.bat), macOS/Linux (.sh), Android (Termux), Docker |
| **Performance Benchmarks** | Load testing tests + documentation |

### Technical Debt
- [x] Webhook security middleware - ✅ app/middleware/webhook_security.py
- [x] Async SQLAlchemy support - ✅ app/repositories/async_payment_repository.py
- [x] Integration tests for all payment gateways
  - ✅ YooKassa, Tinkoff, RoboKassa, RuStore, SBP, CloudPayments, UnitPay, Apple Pay, Google Pay
- [x] API v2 structure - ✅ app/api/v2/ + middleware/api_versioning.py
- [x] API v2 health endpoints - ✅ app/api/v2/routes/health.py (/health, /ready, /live)
- [x] OpenAPI/Swagger documentation - ✅ /docs, /redoc
- [x] CI/CD pipeline - ✅ .github/workflows/ci.yml
- [x] Multi-platform deploy configs - ✅ 14 deployment configurations
- [x] Distributed tracing (OpenTelemetry) - ✅ app/utils/opentelemetry.py + docs/OPENTELEMETRY.md
- [x] Comprehensive error codes documentation - ✅ docs/ERROR_CODES.md
- [ ] API v2 endpoints implementation (payments, webhooks, admin, etc.)
- [x] PostgreSQL migration (alembic.ini switched to PostgreSQL) - ✅ + docker-compose.dev.yml, DEVELOPMENT.md
- [x] Flower dashboard deployment (configured but needs deployment) - ✅ Auth, persistent storage, docs/FLOWER_DEPLOYMENT.md
- [x] Webhook signature verification - ✅ app/utils/webhook_signature.py + tests (21 tests)
- [x] Apple Pay / Google Pay integration - ✅ payment_gateways + schemas + routes
- [x] GraphQL improvements - ✅ schema.py + resolvers.py (Relay pagination, new types)

### GraphQL (Relay-style API)
- [x] **GraphQL Schema** - ✅ app/graphql/schema.py
  - Payment, PaymentEdge, PaymentConnection types
  - Tenant, TenantConnection types
  - WebhookEvent, WebhookEventConnection types
  - PaymentStatusEnum, CurrencyEnum, WebhookEventType, WebhookEventStatus enums
  - PaymentFilterInput, PaginationInput inputs
- [x] **GraphQL Resolvers** - ✅ app/graphql/resolvers.py
  - Payment queries (payment, payment_by_id, payments, payments_by_cursor, statistics)
  - Tenant queries (tenant, tenant_by_api_key, tenants)
  - WebhookEvent queries (webhook_event, webhook_events)
  - Relay cursor pagination (encode_cursor, decode_cursor)
  - Enhanced statistics (by_currency, daily_revenue, average_payment)

### Authentication & Security
- [x] **OAuth2/JWT Authentication** - ✅ app/routes/auth_routes.py
  - Access token + Refresh token
  - Password hashing (bcrypt)
  - Role-based access control (RBAC)
- [x] **2FA (Two-Factor Authentication)** - ✅ app/services/mfa_service.py, app/routes/mfa_routes.py
  - TOTP (Time-based One-Time Password) via pyotp
  - Google Authenticator compatibility
  - QR code setup
  - Backup codes (10 codes per user)
  - 28 tests for 2FA functionality
- [x] **Webhook Signature Verification** - ✅ app/utils/webhook_signature.py
  - HMAC-SHA256 signature validation
  - Timestamp verification
  - Tests for all payment gateways

### Future Enhancements
- [ ] Recurring payments / subscriptions API
- [ ] Split payments / marketplace support
- [ ] Fraud detection integration
- [ ] Mobile SDK (iOS/Android)
- [ ] Multi-language support (i18n)
- [ ] Admin dashboard with analytics
- [ ] Audit logging for admin actions
- [ ] Background task monitoring dashboard (Flower integration)
