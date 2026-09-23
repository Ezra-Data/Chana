"""
WebSocket endpoint — authenticates via JWT in query params, then maintains connection.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.user import User
from app.services.ws_manager import manager

router = APIRouter(tags=["WebSocket"])


async def _authenticate_ws(token: str) -> dict | None:
    """Validate JWT from WebSocket query param and return user info."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        sub = payload.get("sub")
        role = payload.get("role")
        if sub is None:
            return None
        user_id = int(sub)

        # Verify user exists and is active
        async with async_session() as db:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if not user or not user.is_active:
                return None
            return {"user_id": user.id, "role": user.role.value, "name": user.name}

    except (JWTError, ValueError):
        return None


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    """
    WebSocket connection endpoint.
    Client connects with: ws://host/ws?token=<JWT>
    """
    # Authenticate
    user_info = await _authenticate_ws(token)
    if not user_info:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    user_id = user_info["user_id"]
    role = user_info["role"]

    # Register connection
    await manager.connect(user_id, role, websocket)

    try:
        # Keep connection alive, listen for client messages
        while True:
            data = await websocket.receive_text()
            # Client can send ping/heartbeat messages
            if data == "ping":
                await websocket.send_json({"event": "pong", "data": None})
    except WebSocketDisconnect:
        manager.disconnect(user_id, role)
    except Exception:
        manager.disconnect(user_id, role)
