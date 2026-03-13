from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator
import os

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi.errors import RateLimitExceeded

import logging

from app.routes.payment_routes import router as payment_router
from app.routes.webhook_routes import router as webhook_router
from app.routes.admin_routes import router as admin_router
from app.routes.auth_routes import router as auth_router
from app.routes.webhook_monitor_routes import router as webhook_monitor_router
from app.database import init_db, engine, Base
from app.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from app.utils.logger import setup_logging
from app.utils.settings_validator import settings_validator
from app.settings import settings
from app.payment_gateways.exceptions import PaymentGatewayError
from app.utils.metrics import PrometheusMiddleware, MetricsEndpoint

# API Versioning
from app.api.v1 import router as v1_router
from app.api.v2 import router as v2_router

# GraphQL
from strawberry.fastapi import GraphQLRouter
from app.graphql.resolvers import schema as graphql_schema

# WebSocket
from app.routes.websocket_routes import router as websocket_router

setup_logging(level=settings.log_level, json_logs=settings.json_logs)
logger = logging.getLogger(__name__)

# Отключаем rate limiting и middleware для тестов
DISABLE_RATE_LIMITING = os.getenv("DISABLE_RATE_LIMITING", "false").lower() == "true"

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager с graceful shutdown."""
    logger.info("Application startup initiated")

    settings_validator.validate_all(
        yookassa_key=settings.yookassa_api_key,
        yookassa_secret=settings.yookassa_secret_key,
        tinkoff_key=settings.tinkoff_api_key,
        tinkoff_secret=settings.tinkoff_secret_key,
        cloudpayments_key=settings.cloudpayments_api_key,
        cloudpayments_secret=settings.cloudpayments_secret_key,
        unitpay_key=settings.unitpay_api_key,
        unitpay_secret=settings.unitpay_secret_key,
        robokassa_key=settings.robokassa_api_key,
        robokassa_secret=settings.robokassa_secret_key,
        secret_key=settings.secret_key,
        database_url=settings.database_url,
    )

    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.exception(f"Database initialization failed: {e}")
        raise

    logger.info(f"Application started in {'debug' if settings.debug else 'production'} mode")
    yield

    logger.info("Application shutdown initiated")
    try:
        from app.database import engine
        engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


app = FastAPI(
    lifespan=lifespan,
    debug=settings.debug,
    title="FastPay Connect",
    description="API для интеграции с платёжными системами",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(PrometheusMiddleware)

# API Versioning Middleware
from app.middleware.api_versioning import APIVersionMiddleware
app.add_middleware(APIVersionMiddleware)

# TrustedHostMiddleware отключен в тестах
if not DISABLE_RATE_LIMITING and settings.allowed_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

app.state.limiter = limiter

# Добавляем обработчик только для настоящего limiter
if not os.getenv("DISABLE_RATE_LIMITING", "false").lower() == "true":
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

if TEMPLATES_DIR.exists():
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
else:
    templates = None
    logger.warning(f"Templates directory not found: {TEMPLATES_DIR}")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    logger.warning(f"Static directory not found: {STATIC_DIR}")

# Legacy routes (backward compatibility)
app.include_router(payment_router, prefix="/payments", tags=["Payments"])
app.include_router(webhook_router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(admin_router, prefix="/admin/payments", tags=["Admin"])
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])

# Monitoring routes
app.include_router(webhook_monitor_router, prefix="/api/monitoring/webhooks", tags=["Webhook Monitoring"])

# API Versioning
app.include_router(v1_router, prefix="/api/v1", tags=["API v1"])
app.include_router(v2_router, prefix="/api/v2", tags=["API v2"])

# GraphQL
graphql_router = GraphQLRouter(graphql_schema)
app.include_router(graphql_router, prefix="/graphql", tags=["GraphQL"])

# WebSocket
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Главная страница."""
    if not templates:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Templates not available",
        )
    try:
        return templates.TemplateResponse("home.html", {"request": request})
    except Exception as e:
        logger.exception(f"Error rendering home page: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/health", tags=["Health"])
async def health_check():
    """Проверка здоровья приложения."""
    from app.database import engine
    import time
    
    start_time = time.time()
    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(Base.metadata.tables["payments"].select().limit(1))
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "debug": settings.debug,
        "checks": {
            "database": db_status,
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }
    }


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Проверка готовности приложения."""
    readiness_status = {
        "status": "ready",
        "checks": {
            "database": "ok",
            "configuration": "ok",
            "celery": "ok" if settings.celery_enabled else "disabled",
        },
    }

    try:
        from app.database import engine, Base
        with engine.connect() as conn:
            conn.execute(Base.metadata.tables["payments"].select().limit(1))
    except Exception as e:
        readiness_status["status"] = "not_ready"
        readiness_status["checks"]["database"] = f"error: {str(e)}"
        logger.warning(f"Database readiness check failed: {e}")

    if not settings_validator.validate_all(
        yookassa_key=settings.yookassa_api_key,
        yookassa_secret=settings.yookassa_secret_key,
        tinkoff_key=settings.tinkoff_api_key,
        tinkoff_secret=settings.tinkoff_secret_key,
        cloudpayments_key=settings.cloudpayments_api_key,
        cloudpayments_secret=settings.cloudpayments_secret_key,
        unitpay_key=settings.unitpay_api_key,
        unitpay_secret=settings.unitpay_secret_key,
        robokassa_key=settings.robokassa_api_key,
        robokassa_secret=settings.robokassa_secret_key,
        secret_key=settings.secret_key,
        database_url=settings.database_url,
    ):
        readiness_status["status"] = "not_ready"
        readiness_status["checks"]["configuration"] = "missing_required_settings"

    # Проверка подключения к Redis для Celery
    if settings.celery_enabled:
        try:
            import redis
            from redis.exceptions import RedisError
            redis_client = redis.from_url(settings.redis_url)
            redis_client.ping()
            readiness_status["checks"]["redis"] = "ok"
        except ImportError:
            readiness_status["checks"]["redis"] = "redis package not installed"
            readiness_status["status"] = "degraded"
        except RedisError as e:
            readiness_status["checks"]["redis"] = f"error: {str(e)}"
            readiness_status["status"] = "degraded"
            logger.warning(f"Redis connection check failed: {e}")

    if readiness_status["status"] == "ready":
        return readiness_status

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=readiness_status,
    )


@app.get("/health/celery", tags=["Health"])
async def celery_health_check():
    """Проверка здоровья Celery worker."""
    if not settings.celery_enabled:
        return {"status": "disabled", "message": "Celery is disabled"}

    try:
        from app.tasks.webhook_tasks import health_check as celery_health_task
        
        # Отправляем задачу проверки здоровья
        result = celery_health_task.delay()
        result_value = result.get(timeout=10)
        
        return {
            "status": "healthy",
            "celery": result_value,
        }
    except ImportError as e:
        return {
            "status": "error",
            "message": f"Celery not installed: {str(e)}",
        }
    except Exception as e:
        logger.exception(f"Celery health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Celery health check failed: {str(e)}",
        }


app.add_route("/metrics", MetricsEndpoint.metrics)


@app.exception_handler(PaymentGatewayError)
async def payment_gateway_error_handler(request: Request, exc: PaymentGatewayError):
    """Обработчик исключений платёжных шлюзов."""
    logger.warning(f"Payment gateway error: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"error": exc.message, "details": exc.details},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Обработчик непредвиденных ошибок."""
    logger.exception(f"Unhandled error: {exc}")

    accept_header = request.headers.get("accept", "")
    is_api_request = (
        request.url.path.startswith("/api") or
        request.url.path.startswith("/payments") or
        request.url.path.startswith("/webhooks") or
        request.url.path.startswith("/admin") or
        "application/json" in accept_header
    )

    if is_api_request:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal Server Error",
                "message": "Something went wrong, please try again later.",
            },
        )

    return HTMLResponse(
        status_code=500,
        content="Something went wrong, please try again later.",
    )
