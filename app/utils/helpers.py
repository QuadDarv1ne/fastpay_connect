import hashlib
import json
from typing import Dict, Any

def generate_hash(data: str) -> str:
    """
    Генерирует хеш для строки данных с использованием алгоритма SHA-256.

    :param data: Входная строка данных.
    :return: Хеш строки в формате hex.
    """
    return hashlib.sha256(data.encode('utf-8')).hexdigest()

def parse_json(json_data: str) -> Dict[str, Any]:
    """
    Преобразует строку JSON в Python-словарь.

    :param json_data: Строка в формате JSON.
    :return: Python-словарь, представляющий данные.
    :raises ValueError: Если строка не является корректным JSON.
    """
    try:
        return json.loads(json_data)
    except ValueError as e:
        raise ValueError("Invalid JSON data") from e

def validate_payment_amount(amount: float) -> bool:
    """
    Проверяет, что сумма платежа является положительным числом.

    :param amount: Сумма платежа.
    :return: True, если сумма больше 0, иначе False.
    """
    return amount > 0
