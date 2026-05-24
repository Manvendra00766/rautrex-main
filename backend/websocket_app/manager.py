import asyncio
import json
from typing import Dict, Set, Any
from fastapi import WebSocket
from core.logger import logger
import time

class ConnectionManager:
    def __init__(self):
        # Maps client_id to their WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        # Maps channel name to a set of client_ids
        self.channel_subscriptions: Dict[str, Set[str]] = {}
        # Maps client_id to last pong timestamp for heartbeat tracking
        self.last_pongs: Dict[str, float] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.last_pongs[client_id] = time.time()
        logger.info(f"WebSocket Client connected: {client_id}. Total active: {len(self.active_connections)}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        if client_id in self.last_pongs:
            del self.last_pongs[client_id]
        
        # Remove from all channels
        empty_channels = []
        for channel, subscribers in self.channel_subscriptions.items():
            if client_id in subscribers:
                subscribers.remove(client_id)
            if not subscribers:
                empty_channels.append(channel)
                
        for channel in empty_channels:
            del self.channel_subscriptions[channel]
            
        logger.info(f"WebSocket Client disconnected: {client_id}")

    def subscribe(self, client_id: str, channel: str):
        if channel not in self.channel_subscriptions:
            self.channel_subscriptions[channel] = set()
        self.channel_subscriptions[channel].add(client_id)
        logger.debug(f"Client {client_id} subscribed to {channel}")

    def unsubscribe(self, client_id: str, channel: str):
        if channel in self.channel_subscriptions and client_id in self.channel_subscriptions[channel]:
            self.channel_subscriptions[channel].remove(client_id)
            if not self.channel_subscriptions[channel]:
                del self.channel_subscriptions[channel]
        logger.debug(f"Client {client_id} unsubscribed from {channel}")

    async def broadcast_to_channel(self, channel: str, message: dict):
        if channel not in self.channel_subscriptions:
            return
            
        subscribers = self.channel_subscriptions[channel]
        if not subscribers:
            return

        dead_clients = []
        message_str = json.dumps(message)
        
        for client_id in list(subscribers):
            ws = self.active_connections.get(client_id)
            if ws:
                try:
                    await ws.send_text(message_str)
                except Exception as e:
                    logger.warning(f"Failed to send to client {client_id}: {e}")
                    dead_clients.append(client_id)
            else:
                dead_clients.append(client_id)
                
        for client_id in dead_clients:
            self.disconnect(client_id)

    async def heartbeat_loop(self):
        """Continuously check for dead connections and send pings."""
        while True:
            try:
                now = time.time()
                dead_clients = []
                
                for client_id, ws in list(self.active_connections.items()):
                    # If no pong received for > 60 seconds, consider dead
                    if now - self.last_pongs.get(client_id, now) > 60:
                        logger.warning(f"Client {client_id} timed out. Disconnecting.")
                        dead_clients.append(client_id)
                    else:
                        try:
                            await ws.send_text(json.dumps({"type": "ping", "timestamp": now}))
                        except Exception:
                            dead_clients.append(client_id)
                
                for client_id in dead_clients:
                    self.disconnect(client_id)
                    
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                
            await asyncio.sleep(15) # Check every 15 seconds

    def update_pong(self, client_id: str):
        self.last_pongs[client_id] = time.time()

manager = ConnectionManager()
