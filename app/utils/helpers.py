import hashlib
import json
from typing import Any, Dict


def generate_hash(data: str) -> str:
    """Генерирует SHA-256 хеш для строки."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def parse_json(json_data: str) -> Dict[str, Any]:
    """Преобразует JSON строку в словарь."""
    try:
        return json.loads(json_data)
    except json.JSONDecodeError as e:
        raise ValueError("Invalid JSON data") from e


def validate_payment_amount(amount: float) -> bool:
    """Проверяет положительность суммы платежа."""
    return amount > 0
