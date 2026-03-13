"""
WebSocket Manager для управления подключениями.
"""

from typing import Dict, List, Set, Optional
from fastapi import WebSocket
import logging
import json
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Менеджер WebSocket подключений."""

    def __init__(self):
        # Активные подключения: {websocket: user_id}
        self.active_connections: Dict[WebSocket, str] = {}
        
        # Подключения по user_id: {user_id: [websockets]}
        self.user_connections: Dict[str, List[WebSocket]] = {}
        
        # Подключения по order_id: {order_id: [websockets]}
        self.order_subscriptions: Dict[str, Set[WebSocket]] = {}
        
        # Подключения по gateway: {gateway: [websockets]}
        self.gateway_subscriptions: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> bool:
        """
        Принять WebSocket подключение.
        
        Args:
            websocket: WebSocket соединение
            user_id: ID пользователя
            
        Returns:
            True если подключение успешно
        """
        try:
            await websocket.accept()
            self.active_connections[websocket] = user_id
            
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)
            
            logger.info(f"WebSocket connected: user_id={user_id}, total_connections={len(self.active_connections)}")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            return False

    def disconnect(self, websocket: WebSocket):
        """
        Закрыть WebSocket подключение.
        
        Args:
            websocket: WebSocket соединение
        """
        if websocket not in self.active_connections:
            return
        
        user_id = self.active_connections[websocket]
        
        # Удаляем из активных подключений
        del self.active_connections[websocket]
        
        # Удаляем из подключений пользователя
        if user_id in self.user_connections:
            self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Удаляем из подписок
        self._remove_from_subscriptions(websocket)
        
        logger.info(f"WebSocket disconnected: user_id={user_id}, total_connections={len(self.active_connections)}")

    def _remove_from_subscriptions(self, websocket: WebSocket):
        """Удалить подключение из всех подписок."""
        for order_id in list(self.order_subscriptions.keys()):
            if websocket in self.order_subscriptions[order_id]:
                self.order_subscriptions[order_id].remove(websocket)
                if not self.order_subscriptions[order_id]:
                    del self.order_subscriptions[order_id]
        
        for gateway in list(self.gateway_subscriptions.keys()):
            if websocket in self.gateway_subscriptions[gateway]:
                self.gateway_subscriptions[gateway].remove(websocket)
                if not self.gateway_subscriptions[gateway]:
                    del self.gateway_subscriptions[gateway]

    async def send_personal_message(self, message: dict, websocket: WebSocket) -> bool:
        """
        Отправить сообщение конкретному подключению.
        
        Args:
            message: Сообщение для отправки
            websocket: WebSocket соединение
            
        Returns:
            True если сообщение отправлено успешно
        """
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    async def broadcast_to_user(self, message: dict, user_id: str) -> int:
        """
        Отправить сообщение всем подключениям пользователя.
        
        Args:
            message: Сообщение для отправки
            user_id: ID пользователя
            
        Returns:
            Количество успешных отправок
        """
        sent_count = 0
        
        if user_id in self.user_connections:
            for websocket in self.user_connections[user_id]:
                if await self.send_personal_message(message, websocket):
                    sent_count += 1
        
        return sent_count

    async def broadcast_to_order_subscribers(self, message: dict, order_id: str) -> int:
        """
        Отправить сообщение всем подписчикам заказа.
        
        Args:
            message: Сообщение для отправки
            order_id: ID заказа
            
        Returns:
            Количество успешных отправок
        """
        sent_count = 0
        
        if order_id in self.order_subscriptions:
            for websocket in self.order_subscriptions[order_id]:
                if await self.send_personal_message(message, websocket):
                    sent_count += 1
        
        return sent_count

    async def broadcast_to_gateway_subscribers(self, message: dict, gateway: str) -> int:
        """
        Отправить сообщение всем подписчикам gateway.
        
        Args:
            message: Сообщение для отправки
            gateway: Название gateway
            
        Returns:
            Количество успешных отправок
        """
        sent_count = 0
        
        if gateway in self.gateway_subscriptions:
            for websocket in self.gateway_subscriptions[gateway]:
                if await self.send_personal_message(message, websocket):
                    sent_count += 1
        
        return sent_count

    async def broadcast(self, message: dict) -> int:
        """
        Отправить сообщение всем подключениям.
        
        Args:
            message: Сообщение для отправки
            
        Returns:
            Количество успешных отправок
        """
        sent_count = 0
        
        for websocket in list(self.active_connections.keys()):
            if await self.send_personal_message(message, websocket):
                sent_count += 1
        
        return sent_count

    def subscribe_to_order(self, websocket: WebSocket, order_id: str):
        """
        Подписать подключение на уведомления о заказе.
        
        Args:
            websocket: WebSocket соединение
            order_id: ID заказа
        """
        if order_id not in self.order_subscriptions:
            self.order_subscriptions[order_id] = set()
        self.order_subscriptions[order_id].add(websocket)
        
        logger.info(f"WebSocket subscribed to order: order_id={order_id}")

    def subscribe_to_gateway(self, websocket: WebSocket, gateway: str):
        """
        Подписать подключение на уведомления о gateway.
        
        Args:
            websocket: WebSocket соединение
            gateway: Название gateway
        """
        if gateway not in self.gateway_subscriptions:
            self.gateway_subscriptions[gateway] = set()
        self.gateway_subscriptions[gateway].add(websocket)
        
        logger.info(f"WebSocket subscribed to gateway: gateway={gateway}")

    def unsubscribe_from_order(self, websocket: WebSocket, order_id: str):
        """
        Отписать подключение от уведомлений о заказе.
        
        Args:
            websocket: WebSocket соединение
            order_id: ID заказа
        """
        if order_id in self.order_subscriptions:
            self.order_subscriptions[order_id].discard(websocket)
            if not self.order_subscriptions[order_id]:
                del self.order_subscriptions[order_id]

    def unsubscribe_from_gateway(self, websocket: WebSocket, gateway: str):
        """
        Отписать подключение от уведомлений о gateway.
        
        Args:
            websocket: WebSocket соединение
            gateway: Название gateway
        """
        if gateway in self.gateway_subscriptions:
            self.gateway_subscriptions[gateway].discard(websocket)
            if not self.gateway_subscriptions[gateway]:
                del self.gateway_subscriptions[gateway]

    def get_stats(self) -> dict:
        """
        Получить статистику подключений.
        
        Returns:
            Статистика подключений
        """
        return {
            "total_connections": len(self.active_connections),
            "unique_users": len(self.user_connections),
            "order_subscriptions": len(self.order_subscriptions),
            "gateway_subscriptions": len(self.gateway_subscriptions),
        }


# Глобальный экземпляр менеджера
websocket_manager = ConnectionManager()
