from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
import logging
from app.routes.payment_routes import router as payment_router
from app.routes.webhook_routes import router as webhook_router
from app.routes.admin_routes import router as admin_router
from app.database import init_db
from app.middleware.rate_limiter import limiter, rate_limit_exceeded_handler
from app.utils.logger import setup_logging
from app.utils.settings_validator import settings_validator
from app.config import (
    YOOKASSA_API_KEY,
    YOOKASSA_SECRET_KEY,
    TINKOFF_API_KEY,
    TINKOFF_SECRET_KEY,
    CLOUDPAYMENTS_API_KEY,
    CLOUDPAYMENTS_SECRET_KEY,
    UNITPAY_API_KEY,
    UNITPAY_SECRET_KEY,
    ROBOKASSA_API_KEY,
    ROBOKASSA_SECRET_KEY,
    SECRET_KEY,
    DATABASE_URL,
    ALLOWED_ORIGINS,
    DEBUG,
)

setup_logging(level="INFO")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager."""
    settings_validator.validate_all(
        yookassa_key=YOOKASSA_API_KEY,
        yookassa_secret=YOOKASSA_SECRET_KEY,
        tinkoff_key=TINKOFF_API_KEY,
        tinkoff_secret=TINKOFF_SECRET_KEY,
        cloudpayments_key=CLOUDPAYMENTS_API_KEY,
        cloudpayments_secret=CLOUDPAYMENTS_SECRET_KEY,
        unitpay_key=UNITPAY_API_KEY,
        unitpay_secret=UNITPAY_SECRET_KEY,
        robokassa_key=ROBOKASSA_API_KEY,
        robokassa_secret=ROBOKASSA_SECRET_KEY,
        secret_key=SECRET_KEY,
        database_url=DATABASE_URL,
    )
    init_db()
    logger.info("Application started")
    yield


app = FastAPI(lifespan=lifespan, debug=DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(payment_router, prefix="/payments", tags=["payments"])
app.include_router(webhook_router, prefix="/webhooks", tags=["webhooks"])
app.include_router(admin_router, prefix="/admin/payments", tags=["admin"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Главная страница."""
    try:
        return templates.TemplateResponse("home.html", {"request": request})
    except Exception as e:
        logger.error(f"Error rendering home page: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения."""
    return {"status": "healthy"}


@app.get("/ready")
async def readiness_check():
    """Проверка готовности приложения."""
    is_valid = settings_validator.validate_all(
        yookassa_key=YOOKASSA_API_KEY,
        yookassa_secret=YOOKASSA_SECRET_KEY,
        tinkoff_key=TINKOFF_API_KEY,
        tinkoff_secret=TINKOFF_SECRET_KEY,
        cloudpayments_key=CLOUDPAYMENTS_API_KEY,
        cloudpayments_secret=CLOUDPAYMENTS_SECRET_KEY,
        unitpay_key=UNITPAY_API_KEY,
        unitpay_secret=UNITPAY_SECRET_KEY,
        robokassa_key=ROBOKASSA_API_KEY,
        robokassa_secret=ROBOKASSA_SECRET_KEY,
        secret_key=SECRET_KEY,
        database_url=DATABASE_URL,
    )
    if is_valid:
        return {"status": "ready"}
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "not_ready"},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Обработчик ошибок."""
    logger.error(f"Unhandled error: {exc}")
    return HTMLResponse(status_code=500, content="Something went wrong, please try again later.")
