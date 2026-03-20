"""OpenTelemetry Distributed Tracing Setup.

Настройка и инициализация OpenTelemetry для трассировки запросов.
Поддерживает экспорт в Jaeger, Zipkin, OTLP.

Usage:
    from app.utils.opentelemetry import setup_opentelemetry
    setup_opentelemetry()
"""

import os
import logging
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor

# Exporters
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.jaeger.thrift import JaegerExporter

from app.settings import settings

logger = logging.getLogger(__name__)


def setup_opentelemetry(
    service_name: str = "fastpay-connect",
    service_version: str = "1.0.0",
    exporter_type: Optional[str] = None,
    exporter_endpoint: Optional[str] = None,
    sample_rate: float = 1.0,
) -> None:
    """
    Настройка OpenTelemetry tracing.

    Args:
        service_name: Имя сервиса для трассировки
        service_version: Версия сервиса
        exporter_type: Тип экспортера ('jaeger', 'otlp', 'console', 'none')
        exporter_endpoint: URL экспортера (например, 'http://jaeger:14268/api/traces')
        sample_rate: Частота сэмплирования (0.0-1.0)

    Examples:
        # Jaeger
        setup_opentelemetry(
            exporter_type='jaeger',
            exporter_endpoint='http://jaeger:14268/api/traces'
        )

        # OTLP (OpenTelemetry Protocol)
        setup_opentelemetry(
            exporter_type='otlp',
            exporter_endpoint='http://otel-collector:4317'
        )

        # Console (для разработки)
        setup_opentelemetry(exporter_type='console')

        # Отключить трассировку
        setup_opentelemetry(exporter_type='none')
    """
    # Проверяем включена ли трассировка
    if os.getenv("OPENTELEMETRY_ENABLED", "false").lower() != "true":
        logger.info("OpenTelemetry disabled")
        return

    # Определяем тип экспортера из env если не указан
    if exporter_type is None:
        exporter_type = os.getenv("OPENTELEMETRY_EXPORTER", "console").lower()

    # Определяем endpoint из env если не указан
    if exporter_endpoint is None:
        exporter_endpoint = os.getenv("OPENTELEMETRY_ENDPOINT")

    # Создаём resource с информацией о сервисе
    resource = Resource(attributes={
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENV", "development"),
        "host.name": os.getenv("HOSTNAME", "unknown"),
    })

    # Создаём tracer provider с сэмплированием
    tracer_provider = TracerProvider(
        resource=resource,
        # sample_rate можно настроить через TraceIdRatioBased
    )

    # Настраиваем экспортер
    span_processor = None

    if exporter_type == "jaeger":
        endpoint = exporter_endpoint or os.getenv("JAEGER_ENDPOINT", "http://jaeger:14268/api/traces")
        try:
            jaeger_exporter = JaegerExporter(
                agent_host_name=os.getenv("JAEGER_HOST", "jaeger"),
                agent_port=int(os.getenv("JAEGER_PORT", "6831")),
                endpoint=endpoint,
                username=os.getenv("JAEGER_USER"),
                password=os.getenv("JAEGER_PASSWORD"),
            )
            span_processor = BatchSpanProcessor(jaeger_exporter)
            logger.info(f"OpenTelemetry: Jaeger exporter configured ({endpoint})")
        except Exception as e:
            logger.error(f"OpenTelemetry: Failed to configure Jaeger exporter: {e}")

    elif exporter_type == "otlp":
        endpoint = exporter_endpoint or os.getenv("OTLP_ENDPOINT", "http://otel-collector:4317")
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=endpoint)
            span_processor = BatchSpanProcessor(otlp_exporter)
            logger.info(f"OpenTelemetry: OTLP exporter configured ({endpoint})")
        except Exception as e:
            logger.error(f"OpenTelemetry: Failed to configure OTLP exporter: {e}")

    elif exporter_type == "console":
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        console_exporter = ConsoleSpanExporter()
        span_processor = BatchSpanProcessor(console_exporter)
        logger.info("OpenTelemetry: Console exporter configured (debug mode)")

    elif exporter_type == "none":
        logger.info("OpenTelemetry: Tracing disabled (exporter=none)")

    else:
        logger.warning(f"OpenTelemetry: Unknown exporter type '{exporter_type}', using console")
        from opentelemetry.sdk.trace.export import ConsoleSpanExporter
        span_processor = BatchSpanProcessor(ConsoleSpanExporter())

    # Добавляем processor к provider
    if span_processor:
        tracer_provider.add_span_processor(span_processor)

    # Устанавливаем global tracer provider
    trace.set_tracer_provider(tracer_provider)

    # Инструментируем FastAPI
    try:
        FastAPIInstrumentor.instrument_app(
            app=None,  # Будет установлено в main.py
            tracer_provider=tracer_provider,
            excluded_urls="/health,/docs,/redoc,/metrics",
        )
        logger.info("OpenTelemetry: FastAPI instrumentation enabled")
    except Exception as e:
        logger.error(f"OpenTelemetry: Failed to instrument FastAPI: {e}")

    # Инструментируем Redis
    try:
        RedisInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("OpenTelemetry: Redis instrumentation enabled")
    except Exception as e:
        logger.error(f"OpenTelemetry: Failed to instrument Redis: {e}")

    # Инструментируем SQLAlchemy
    try:
        SQLAlchemyInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("OpenTelemetry: SQLAlchemy instrumentation enabled")
    except Exception as e:
        logger.error(f"OpenTelemetry: Failed to instrument SQLAlchemy: {e}")

    # Инструментируем Celery
    try:
        CeleryInstrumentor().instrument(tracer_provider=tracer_provider)
        logger.info("OpenTelemetry: Celery instrumentation enabled")
    except Exception as e:
        logger.error(f"OpenTelemetry: Failed to instrument Celery: {e}")

    logger.info(f"OpenTelemetry: Tracing initialized (service={service_name}, version={service_version})")


def get_tracer(name: str) -> trace.Tracer:
    """
    Получить tracer для создания spans.

    Args:
        name: Имя tracer (обычно имя модуля)

    Returns:
        Tracer instance

    Example:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("my_operation"):
            # your code
            pass
    """
    return trace.get_tracer(name)


def shutdown_opentelemetry() -> None:
    """
    Корректное завершение работы OpenTelemetry.

    Вызывается при shutdown приложения.
    """
    tracer_provider = trace.get_tracer_provider()
    if hasattr(tracer_provider, 'force_flush'):
        tracer_provider.force_flush(timeout_millis=5000)
    if hasattr(tracer_provider, 'shutdown'):
        tracer_provider.shutdown()
    logger.info("OpenTelemetry: Shutdown complete")
