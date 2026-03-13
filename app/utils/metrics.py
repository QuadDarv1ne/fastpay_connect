"""Prometheus metrics для мониторинга приложения."""

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
import time
import re
from typing import Dict, Optional

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

REQUEST_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
)

PAYMENT_CREATED = Counter(
    "payments_created_total",
    "Total payments created",
    ["gateway", "status"],
)

WEBHOOK_RECEIVED = Counter(
    "webhooks_received_total",
    "Total webhooks received",
    ["gateway", "event_type"],
)

DB_CONNECTIONS = Gauge(
    "database_connections_active",
    "Number of active database connections",
)


def sanitize_endpoint(endpoint: str) -> str:
    """Sanitize endpoint for Prometheus labels."""
    endpoint = re.sub(r"/\d+", "/{id}", endpoint)
    endpoint = re.sub(r"/[a-f0-9-]{36}", "/{uuid}", endpoint)
    return endpoint.replace("/", "_").strip("_") or "root"


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware для сбора метрик Prometheus."""

    async def dispatch(self, request: Request, call_next) -> Response:
        method = request.method
        endpoint = sanitize_endpoint(request.url.path)

        REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()

        start_time = time.time()

        try:
            response = await call_next(request)

            duration = time.time() - start_time
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status_code=response.status_code,
            ).inc()
            REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()

            return response
        except Exception:
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
            raise


def track_payment(gateway: str, status: str) -> None:
    """Отследить создание платежа."""
    PAYMENT_CREATED.labels(gateway=gateway, status=status).inc()


def track_webhook(gateway: str, event_type: str) -> None:
    """Отследить получение webhook."""
    WEBHOOK_RECEIVED.labels(gateway=gateway, event_type=event_type).inc()


def update_db_connections(count: int) -> None:
    """Обновить счётчик активных подключений к БД."""
    DB_CONNECTIONS.set(count)


class MetricsEndpoint:
    """Endpoint для экспорта метрик Prometheus."""

    @staticmethod
    async def metrics() -> Response:
        """Export Prometheus metrics."""
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )
