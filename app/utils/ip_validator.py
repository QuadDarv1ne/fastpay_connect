import ipaddress
import logging
from typing import List, Optional
from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def is_ip_in_whitelist(ip: str, whitelist: List[str]) -> bool:
    """Проверка IP в whitelist (поддерживает CIDR)."""
    try:
        client_ip = ipaddress.ip_address(ip)
        for allowed in whitelist:
            if "/" in allowed:
                if client_ip in ipaddress.ip_network(allowed, strict=False):
                    return True
            else:
                if client_ip == ipaddress.ip_address(allowed):
                    return True
        return False
    except (ValueError, TypeError):
        return False


async def verify_webhook_ip(request: Request, whitelist: List[str]) -> None:
    """Проверка IP запроса. Выбрасывает 403 если IP не в whitelist."""
    client_ip: Optional[str] = request.client.host if request.client else None

    if not client_ip or client_ip in ("127.0.0.1", "localhost"):
        return

    if not is_ip_in_whitelist(client_ip, whitelist):
        logger.warning(f"Webhook access denied from IP: {client_ip}")
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: IP {client_ip} not allowed",
        )
