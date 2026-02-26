import ipaddress
from fastapi import HTTPException, Request
from typing import List


def is_ip_in_whitelist(ip: str, whitelist: List[str]) -> bool:
    """
    Проверяет, находится ли IP-адрес в белом списке.
    Поддерживает CIDR-notation (например, 192.168.1.0/24).
    """
    try:
        client_ip = ipaddress.ip_address(ip)
        for allowed in whitelist:
            if "/" in allowed:
                # CIDR диапазон
                if client_ip in ipaddress.ip_network(allowed, strict=False):
                    return True
            else:
                # Одиночный IP
                if client_ip == ipaddress.ip_address(allowed):
                    return True
        return False
    except ValueError:
        return False


async def verify_webhook_ip(request: Request, whitelist: List[str]) -> None:
    """
    Проверяет IP-адрес запроса. Если IP не в whitelist — выбрасывает HTTPException 403.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Для локальной разработки пропускаем localhost
    if client_ip in ["127.0.0.1", "localhost", "unknown"]:
        return
    
    if not is_ip_in_whitelist(client_ip, whitelist):
        raise HTTPException(
            status_code=403,
            detail=f"Access denied: IP {client_ip} is not in the allowed list"
        )
