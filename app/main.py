from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

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
from app.database import init_db, engine, Base
from app.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from app.utils.logger import setup_logging
from app.utils.settings_validator import settings_validator
from app.settings import settings
from app.payment_gateways.exceptions import PaymentGatewayError

setup_logging(level=settings.log_level)
logger = logging.getLogger(__name__)

# Пути к статике и шаблонам
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager с graceful shutdown."""
    # Startup
    logger.info("Application startup initiated")

    # Валидация настроек (только логирование, не блокируем запуск)
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

    # Инициализация БД
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.exception(f"Database initialization failed: {e}")
        raise

    logger.info(f"Application started in {'debug' if settings.debug else 'production'} mode")

    yield

    # Shutdown
    logger.info("Application shutdown initiated")
    try:
        await engine.dispose()
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

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.allowed_hosts:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts,
    )

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Шаблоны и статика (опционально)
if TEMPLATES_DIR.exists():
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
else:
    templates = None
    logger.warning(f"Templates directory not found: {TEMPLATES_DIR}")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
else:
    logger.warning(f"Static directory not found: {STATIC_DIR}")

# Роутеры
app.include_router(payment_router, prefix="/payments", tags=["Payments"])
app.include_router(webhook_router, prefix="/webhooks", tags=["Webhooks"])
app.include_router(admin_router, prefix="/admin/payments", tags=["Admin"])


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
    """Проверка здоровья приложения.

    Возвращает статус приложения без проверки зависимостей.
    """
    return {"status": "healthy", "debug": settings.debug}


@app.get("/ready", tags=["Health"])
async def readiness_check():
    """Проверка готовности приложения.

    Проверяет доступность всех критических зависимостей (БД, платёжные шлюзы).
    """
    readiness_status = {
        "status": "ready",
        "checks": {
            "database": "ok",
            "configuration": "ok",
        },
    }

    # Проверка БД
    try:
        async with engine.connect() as conn:
            await conn.execute(Base.metadata.tables["payments"].select().limit(1))
    except Exception as e:
        readiness_status["status"] = "not_ready"
        readiness_status["checks"]["database"] = f"error: {str(e)}"
        logger.warning(f"Database readiness check failed: {e}")

    # Проверка конфигурации
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

    if readiness_status["status"] == "ready":
        return readiness_status

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=readiness_status,
    )


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
    """Обработчик непредвиденных ошибок.

    Возвращает JSON для API запросов и HTML для браузера.
    """
    logger.exception(f"Unhandled error: {exc}")

    # Определяем тип запроса
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
