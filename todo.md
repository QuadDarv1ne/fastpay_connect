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

## Pending

### High Priority
- [ ] Integration tests with mocked payment gateways
- [ ] Webhook retry queue (Celery + Redis)
- [ ] Input validation with Pydantic v2

### Medium Priority
- [ ] Prometheus metrics export
- [ ] Structured JSON logging
- [ ] Pagination for admin endpoints
- [ ] Rate limiting per API key

### Low Priority
- [ ] Multi-currency support
- [ ] Payment statistics dashboard
- [ ] Additional payment systems
