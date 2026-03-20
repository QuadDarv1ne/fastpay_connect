# FastPay Connect - TODO

> **Last Updated**: Mar 2026  
> **Current Branch**: main & dev (synced)  
> **Test Coverage**: 40 test files (~60%+ coverage)  
> **Payment Gateways**: 8 integrated  
> **CI/CD**: GitHub Actions (multi-platform deploy)  
> **Codebase**: 79 Python files (app/), 8 routes, 5 middleware, 5 models, 6 repositories, 4 services, 3 websocket

## Completed

### Core Infrastructure
- [x] Migrate from config.py to settings.py (Pydantic Settings) - ✅ app/settings.py
- [x] PaymentStatus Enum with SQLAlchemy values_callable
- [x] Multi-stage Dockerfile with healthcheck - ✅ Dockerfile (builder + runtime stages)
- [x] Pre-commit hooks (black, flake8, isort, mypy, detect-secrets) - ✅ .pre-commit-config.yaml
- [x] TrustedHostMiddleware for production
- [x] Alembic migrations - ✅ 5 migration files in alembic/versions/
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
- [x] **Services package** - ✅ app/services/__init__.py (4 services total)
- [x] **GraphQL API** - ✅ Strawberry GraphQL with resolvers (app/graphql/)
  - GraphQL schema: app/graphql/schema.py (Payment, PaymentConnection types)
  - GraphQL resolvers: app/graphql/resolvers.py
  - PaymentStatus enum
- [x] **OAuth2/JWT Authentication** - ✅ JWT auth, refresh tokens, password reset
- [x] **WebSocket Notifications** - ✅ app/websocket/ (real-time payment updates)
  - WebSocket router: app/routes/websocket_routes.py
  - Connection manager: app/websocket/manager.py
  - Notifications: app/websocket/notifications.py
  - Package: app/websocket/__init__.py (3 files total)
- [x] **API Versioning** - ✅ v1/v2 structure (app/api/v1/, app/api/v2/)
- [x] **Webhook Security Middleware** - ✅ app/middleware/webhook_security.py
- [x] **Rate limiting per API key** - ✅ app/middleware/rate_limiter.py (slowapi)
- [x] **IP Validator** - ✅ app/utils/ip_validator.py
- [x] **Metrics utility** - ✅ app/utils/metrics.py

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

### Routes & Endpoints
- [x] Payment routes - ✅ app/routes/payment_routes.py
- [x] Webhook routes - ✅ app/routes/webhook_routes.py
- [x] Admin routes - ✅ app/routes/admin_routes.py
- [x] Auth routes - ✅ app/routes/auth_routes.py
- [x] Dashboard routes - ✅ app/routes/dashboard_routes.py
- [x] Webhook monitor routes - ✅ app/routes/webhook_monitor_routes.py
- [x] WebSocket routes - ✅ app/routes/websocket_routes.py
- [x] API v1 router - ✅ app/api/v1/__init__.py (payments, webhooks, admin, auth, health)
- [x] API v2 router - ✅ app/api/v2/__init__.py (development status)

### Middleware (5 total)
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
- [x] Health check endpoints - ✅ /health, /health/celery, /health/db, /health/redis
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
- [x] README.md (308 строк) - ✅ Основная документация проекта

### Static Assets
- [x] Project logo - ✅ fastpay_connect.png
- [x] Static files directory - ✅ app/static/
- [x] Templates directory - ✅ app/templates/ (Jinja2)
- [x] Scripts - ✅ scripts/create_superuser.py, deploy/scripts/deploy.sh

## Pending

### High Priority
- [ ] API v2 endpoints implementation (structure ready: app/api/v2/)
- [ ] Apple Pay / Google Pay integration
- [ ] Mobile SDK (iOS/Android)
- [ ] Performance benchmarks and load testing
- [ ] GraphQL schema improvements (currently basic Strawberry setup)
- [ ] PostgreSQL migration scripts (alembic.ini uses SQLite for dev)

### Medium Priority
- [ ] Payment analytics and reporting API
- [ ] Multi-language support (i18n)
- [ ] Cache service with Redis (currently using in-memory LRUCache)
- [ ] Rate limiting persistence (currently in-memory)
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Webhook signature verification for all gateways (some implemented)
- [ ] Flower dashboard deployment (configured in docker-compose.prod.yml)

### Low Priority
- [ ] Payment statistics dashboard (basic dashboard exists: routes/dashboard_routes.py)
- [ ] Admin dashboard with analytics
- [ ] Export payment data (CSV, Excel, PDF)
- [ ] Webhook management UI (retry, view history)
- [ ] Multi-factor authentication (2FA)
- [ ] Audit logging for admin actions
- [ ] Comprehensive error codes documentation
- [ ] Background task monitoring dashboard (Flower integration)
- [ ] Additional deploy scripts for remaining platforms

---

## Project Health & Quality Metrics

### Current State (Mar 2026)
| Metric | Value |
|--------|-------|
| **Payment Gateways** | 8 (YooKassa, Tinkoff, CloudPayments, UnitPay, RoboKassa, RuStore, SBP) |
| **Test Files** | 40 files (~60%+ coverage) |
| **API Version** | v1 (stable), v2 (structure ready) |
| **Database** | SQLite (dev) / PostgreSQL (prod via Docker) |
| **Async Tasks** | Celery + Redis (webhook retry queue, 5 tasks) |
| **GraphQL** | Strawberry GraphQL API (Payment, PaymentConnection types) |
| **WebSocket** | Real-time notifications |
| **Auth** | OAuth2/JWT with refresh tokens |
| **Multi-tenant** | X-API-Key isolation |
| **Multi-currency** | 10 currencies (RUB base) |
| **CI/CD** | GitHub Actions (test, lint, build, deploy) |
| **Deploy Targets** | 14 configs (AWS, GCP, Cloudflare, K8s, Render, Railway, Fly.io, Vercel, Netlify) |
| **Documentation** | Swagger UI, ReDoc, 7 docs, README (308 lines), deploy/README (250 lines) |
| **Codebase** | 79 Python files, 8 routes, 5 middleware, 5 models, 6 repositories, 4 services, 3 websocket |
| **Static Assets** | Logo, templates (Jinja2), static files, scripts |

### Technical Debt
- [x] Webhook security middleware - ✅ app/middleware/webhook_security.py
- [x] Async SQLAlchemy support - ✅ app/repositories/async_payment_repository.py
- [x] Integration tests for all payment gateways
  - ✅ YooKassa, Tinkoff, RoboKassa, RuStore, SBP, CloudPayments, UnitPay
- [x] API v2 structure - ✅ app/api/v2/ + middleware/api_versioning.py
- [x] OpenAPI/Swagger documentation - ✅ /docs, /redoc
- [x] CI/CD pipeline - ✅ .github/workflows/ci.yml
- [x] Multi-platform deploy configs - ✅ 14 deployment configurations
- [ ] Distributed tracing (OpenTelemetry)
- [ ] Comprehensive error codes documentation
- [ ] API v2 endpoints implementation
- [ ] PostgreSQL migration (alembic.ini defaults to SQLite for dev)
- [ ] Flower dashboard deployment (configured but needs deployment)

### Future Enhancements
- [ ] Recurring payments / subscriptions API
- [ ] Split payments / marketplace support
- [ ] Fraud detection integration
- [ ] Apple Pay / Google Pay integration
- [ ] Mobile SDK (iOS/Android)
- [ ] Payment analytics and reporting API
- [ ] Multi-language support (i18n)
