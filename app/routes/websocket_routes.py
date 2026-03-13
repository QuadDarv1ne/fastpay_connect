"""
WebSocket routes для уведомлений о платежах.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query, HTTPException
from typing import Optional, List
import logging
import json
from datetime import datetime, timezone

from app.websocket.manager import websocket_manager
from app.utils.security import decode_token
from app.database import get_db
from app.repositories.payment_repository import PaymentRepository
from app.dependencies import get_payment_repository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: Optional[str] = Query(default=None, description="JWT access token"),
    order_id: Optional[str] = Query(default=None, description="Subscribe to specific order"),
    gateway: Optional[str] = Query(default=None, description="Subscribe to specific gateway"),
):
    """
    WebSocket endpoint для получения уведомлений о платежах.
    
    Подключение:
        ws://localhost:8080/ws/notifications?token=YOUR_JWT_TOKEN
    
    С подпиской на заказ:
        ws://localhost:8080/ws/notifications?token=YOUR_JWT_TOKEN&order_id=order_123
    
    С подпиской на gateway:
        ws://localhost:8080/ws/notifications?token=YOUR_JWT_TOKEN&gateway=yookassa
    
    Формат сообщений от сервера:
    {
        "type": "payment_updated",
        "data": {
            "order_id": "order_123",
            "payment_id": "pay_123",
            "status": "completed",
            "amount": 1000.00,
            "currency": "RUB",
            "gateway": "yookassa",
            "updated_at": "2026-03-13T12:00:00Z"
        },
        "timestamp": "2026-03-13T12:00:00Z"
    }
    """
    # Проверка токена
    if not token:
        await websocket.close(code=4001, reason="Token required")
        return
    
    # Декодирование токена
    token_data = decode_token(token, expected_type="access")
    
    if not token_data:
        await websocket.close(code=4002, reason="Invalid token")
        return
    
    user_id = str(token_data.user_id)
    
    # Подключение
    connected = await websocket_manager.connect(websocket, user_id)
    
    if not connected:
        await websocket.close(code=4003, reason="Connection failed")
        return
    
    # Отправляем приветственное сообщение
    await websocket.send_json({
        "type": "connected",
        "data": {
            "user_id": user_id,
            "message": "Successfully connected to notifications",
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    
    # Подписка на заказ если указан
    if order_id:
        websocket_manager.subscribe_to_order(websocket, order_id)
        await websocket.send_json({
            "type": "subscribed",
            "data": {"order_id": order_id},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    # Подписка на gateway если указан
    if gateway:
        websocket_manager.subscribe_to_gateway(websocket, gateway)
        await websocket.send_json({
            "type": "subscribed",
            "data": {"gateway": gateway},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    try:
        while True:
            # Получаем сообщения от клиента
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                await handle_client_message(websocket, message, user_id)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid JSON"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected: user_id={user_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)


async def handle_client_message(websocket: WebSocket, message: dict, user_id: str):
    """
    Обработка сообщений от клиента.
    
    Поддерживаемые команды:
    - subscribe: {"action": "subscribe", "order_id": "order_123"}
    - unsubscribe: {"action": "unsubscribe", "order_id": "order_123"}
    - subscribe_gateway: {"action": "subscribe_gateway", "gateway": "yookassa"}
    - unsubscribe_gateway: {"action": "unsubscribe_gateway", "gateway": "yookassa"}
    - get_stats: {"action": "get_stats"}
    """
    action = message.get("action")
    
    if action == "subscribe":
        order_id = message.get("order_id")
        if order_id:
            websocket_manager.subscribe_to_order(websocket, order_id)
            await websocket.send_json({
                "type": "subscribed",
                "data": {"order_id": order_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    
    elif action == "unsubscribe":
        order_id = message.get("order_id")
        if order_id:
            websocket_manager.unsubscribe_from_order(websocket, order_id)
            await websocket.send_json({
                "type": "unsubscribed",
                "data": {"order_id": order_id},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    
    elif action == "subscribe_gateway":
        gateway = message.get("gateway")
        if gateway:
            websocket_manager.subscribe_to_gateway(websocket, gateway)
            await websocket.send_json({
                "type": "subscribed",
                "data": {"gateway": gateway},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    
    elif action == "unsubscribe_gateway":
        gateway = message.get("gateway")
        if gateway:
            websocket_manager.unsubscribe_from_gateway(websocket, gateway)
            await websocket.send_json({
                "type": "unsubscribed",
                "data": {"gateway": gateway},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    
    elif action == "get_stats":
        stats = websocket_manager.get_stats()
        await websocket.send_json({
            "type": "stats",
            "data": stats,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    else:
        await websocket.send_json({
            "type": "error",
            "data": {"message": f"Unknown action: {action}"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


@router.get("/stats")
async def get_websocket_stats():
    """Получить статистику WebSocket подключений."""
    return {
        "status": "success",
        "data": websocket_manager.get_stats(),
    }
