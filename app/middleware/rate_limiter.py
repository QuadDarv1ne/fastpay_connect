from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Обработчик превышения лимита запросов."""
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": "Too Many Requests",
            "message": "Превышен лимит запросов. Пожалуйста, подождите немного.",
            "retry_after": str(exc.detail.headers.get("Retry-After", "60"))
        }
    )
