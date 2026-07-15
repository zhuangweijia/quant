import json
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.services.auth_service import AuthService
from app.ws.manager import ws_manager

logger = structlog.get_logger()

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    user_id = None
    try:
        if not token:
            await websocket.close(code=4001, reason="Missing token")
            return

        payload = AuthService.decode_token(token)
        if not payload or payload.get("type") != "access":
            await websocket.close(code=4001, reason="Invalid token")
            return

        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token payload")
            return

        await ws_manager.connect(websocket, user_id)

        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                action = msg.get("action")
                if action == "ping":
                    await websocket.send_text(json.dumps({"action": "pong"}))
                elif action == "subscribe":
                    channels = msg.get("channels", [])
                    if isinstance(channels, list):
                        await ws_manager.subscribe(websocket, user_id, channels)
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "system",
                                    "data": {"message": "subscribed", "channels": channels},
                                    "timestamp": datetime.now(UTC).isoformat(),
                                }
                            )
                        )
                elif action == "unsubscribe":
                    channels = msg.get("channels", [])
                    if isinstance(channels, list):
                        await ws_manager.unsubscribe(websocket, user_id, channels)
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "system",
                                    "data": {"message": "unsubscribed", "channels": channels},
                                    "timestamp": datetime.now(UTC).isoformat(),
                                }
                            )
                        )
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("ws.error", error=str(e))
    finally:
        if user_id:
            await ws_manager.disconnect(websocket, user_id)
