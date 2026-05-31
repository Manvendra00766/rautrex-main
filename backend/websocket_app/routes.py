import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from .manager import manager
from core.logger import logger
from services.streaming_engine import streaming_engine
import uuid

router = APIRouter()

@router.on_event("startup")
async def start_heartbeat():
    asyncio.create_task(manager.heartbeat_loop())
    asyncio.create_task(manager.start_pubsub_listener())

@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket, client_id: str = Query(None)):
    if not client_id:
        client_id = str(uuid.uuid4())
        
    await manager.connect(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")
                
                if msg_type == "pong":
                    manager.update_pong(client_id)
                elif msg_type == "subscribe":
                    channel = msg.get("channel")
                    if channel:
                        manager.subscribe(client_id, channel)
                        # If subscribing to a ticker channel, register it with the streaming engine
                        if channel.startswith("ticker:"):
                            ticker = channel.split(":", 1)[1].strip().upper()
                            if ticker:
                                streaming_engine.add_ticker(ticker)
                elif msg_type == "unsubscribe":
                    channel = msg.get("channel")
                    if channel:
                        manager.unsubscribe(client_id, channel)
                        # If no more subscribers for this ticker channel, stop tracking it
                        if channel.startswith("ticker:") and channel not in manager.channel_subscriptions:
                            ticker = channel.split(":", 1)[1].strip().upper()
                            streaming_engine.remove_ticker(ticker)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from {client_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        manager.disconnect(client_id)
