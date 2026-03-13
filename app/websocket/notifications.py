"""
WebSocket уведомления для платежей.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.websocket.manager import websocket_manager

logger = logging.getLogger(__name__)


def send_payment_notification(
    order_id: str,
    payment_id: Optional[str],
    status: str,
    amount: float,
    currency: str,
    gateway: str,
    payment_data: Optional[Dict[str, Any]] = None,
) -> int:
    """
    Отправить уведомление об изменении статуса платежа.
    
    Args:
        order_id: ID заказа
        payment_id: ID платежа
        status: Новый статус
        amount: Сумма
        currency: Валюта
        gateway: Платёжная система
        payment_data: Дополнительные данные
        
    Returns:
        Количество отправленных уведомлений
    """
    message = {
        "type": "payment_updated",
        "data": {
            "order_id": order_id,
            "payment_id": payment_id,
            "status": status,
            "amount": amount,
            "currency": currency,
            "gateway": gateway,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **(payment_data or {}),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    sent_count = 0
    
    # Отправляем подписчикам заказа
    sent_count += websocket_manager.broadcast_to_order_subscribers(message, order_id)
    
    # Отправляем подписчикам gateway
    sent_count += websocket_manager.broadcast_to_gateway_subscribers(message, gateway)
    
    if sent_count > 0:
        logger.info(f"Sent {sent_count} WebSocket notifications for payment {order_id}")
    
    return sent_count


def send_payment_created_notification(
    order_id: str,
    payment_id: Optional[str],
    amount: float,
    currency: str,
    gateway: str,
    payment_url: Optional[str] = None,
) -> int:
    """
    Отправить уведомление о создании платежа.
    
    Args:
        order_id: ID заказа
        payment_id: ID платежа
        amount: Сумма
        currency: Валюта
        gateway: Платёжная система
        payment_url: URL для оплаты
        
    Returns:
        Количество отправленных уведомлений
    """
    message = {
        "type": "payment_created",
        "data": {
            "order_id": order_id,
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "gateway": gateway,
            "payment_url": payment_url,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    sent_count = 0
    
    # Отправляем подписчикам заказа
    sent_count += websocket_manager.broadcast_to_order_subscribers(message, order_id)
    
    # Отправляем подписчикам gateway
    sent_count += websocket_manager.broadcast_to_gateway_subscribers(message, gateway)
    
    if sent_count > 0:
        logger.info(f"Sent {sent_count} WebSocket notifications for new payment {order_id}")
    
    return sent_count


def send_payment_error_notification(
    order_id: str,
    error_message: str,
    gateway: str,
) -> int:
    """
    Отправить уведомление об ошибке платежа.
    
    Args:
        order_id: ID заказа
        error_message: Сообщение об ошибке
        gateway: Платёжная система
        
    Returns:
        Количество отправленных уведомлений
    """
    message = {
        "type": "payment_error",
        "data": {
            "order_id": order_id,
            "error": error_message,
            "gateway": gateway,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    sent_count = 0
    
    # Отправляем подписчикам заказа
    sent_count += websocket_manager.broadcast_to_order_subscribers(message, order_id)
    
    if sent_count > 0:
        logger.warning(f"Sent {sent_count} WebSocket error notifications for payment {order_id}")
    
    return sent_count
