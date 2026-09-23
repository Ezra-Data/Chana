"""
WebSocket Connection Manager — native FastAPI/Starlette WebSockets.

Manages per-user connections and provides targeted + broadcast messaging.
"""

import json
import logging
from typing import Dict, Set, Any, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections keyed by user_id."""

    def __init__(self):
        # user_id -> WebSocket connection
        self._connections: Dict[int, WebSocket] = {}
        # role -> set of user_ids (for role-based broadcasting)
        self._role_map: Dict[str, Set[int]] = {
            "student": set(),
            "agent": set(),
            "admin": set(),
        }

    async def connect(self, user_id: int, role: str, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        self._connections[user_id] = websocket
        if role in self._role_map:
            self._role_map[role].add(user_id)
        logger.info(f"WebSocket connected: user_id={user_id}, role={role}")

    def disconnect(self, user_id: int, role: str):
        """Remove a WebSocket connection."""
        self._connections.pop(user_id, None)
        if role in self._role_map:
            self._role_map[role].discard(user_id)
        logger.info(f"WebSocket disconnected: user_id={user_id}")

    async def send_to_user(self, user_id: int, event: str, data: Any):
        """Send a message to a specific user."""
        ws = self._connections.get(user_id)
        if ws:
            try:
                await ws.send_json({"event": event, "data": data})
            except Exception as e:
                logger.error(f"Failed to send to user {user_id}: {e}")
                self._connections.pop(user_id, None)

    async def broadcast_to_role(self, role: str, event: str, data: Any):
        """Broadcast a message to all users of a specific role."""
        user_ids = self._role_map.get(role, set()).copy()
        for user_id in user_ids:
            await self.send_to_user(user_id, event, data)

    async def broadcast_all(self, event: str, data: Any):
        """Broadcast to all connected users."""
        for user_id in list(self._connections.keys()):
            await self.send_to_user(user_id, event, data)

    @property
    def active_connections(self) -> int:
        return len(self._connections)


# Singleton instance
manager = ConnectionManager()
