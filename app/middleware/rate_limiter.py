from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, status
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)


async def rate_limit_exceeded_handler(
    request: Request,
    exc: RateLimitExceeded
) -> JSONResponse:
    """Обработчик превышения лимита запросов."""
    retry_after: Optional[str] = None
    if hasattr(exc, 'detail') and hasattr(exc.detail, 'headers'):
        retry_after = exc.detail.headers.get("Retry-After")

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "success": False,
            "error": "Too Many Requests",
            "message": "Превышен лимит запросов. Пожалуйста, подождите.",
            "retry_after": retry_after or "60",
        },
    )
