import asyncio
import time
from typing import Callable, Dict, Any, Optional
import websockets
from core.logger import logger

class ResilientWebSocketClient:
    """
    ResilientWebSocketClient implements the "Zombie Socket & Auto-Reconnector" pattern.
    It maintains a single active outbound connection to broker feeds, sends active heartbeats,
    detects silent socket deaths (zombie connection), and performs automatic exponential backoff reconnections.
    Supports both standard protocol-level ping/pong frames and custom message-based pings/pongs.
    """
    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        ping_interval: float = 30.0,
        pong_timeout: float = 5.0,
        ping_message: Optional[str] = None,
        pong_message_checker: Optional[Callable[[str], bool]] = None,
        on_message_callback: Optional[Callable[[str], Any]] = None
    ):
        self.url = url
        self.headers = headers or {}
        self.ping_interval = ping_interval
        self.pong_timeout = pong_timeout
        self.ping_message = ping_message
        self.pong_message_checker = pong_message_checker
        self.on_message = on_message_callback
        
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.is_running = False
        self.last_pong_time = time.time()
        self.last_ping_time = 0.0
        
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._listen_task: Optional[asyncio.Task] = None
        self._reconnect_lock = asyncio.Lock()

    async def start(self):
        """Starts the outbound connection and background loops."""
        if self.is_running:
            return
        self.is_running = True
        self.last_pong_time = time.time()
        
        # Connect initially
        await self._connect_with_retry()
        
        # Start background helper tasks
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._listen_task = asyncio.create_task(self._listen_loop())
        logger.info(f"[ResilientWS] Outbound client loops started for {self.url}")

    async def stop(self):
        """Clean shutdown of loops and sockets."""
        self.is_running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._listen_task:
            self._listen_task.cancel()
        if self.ws:
            await self.ws.close()
            logger.info("[ResilientWS] Socket closed cleanly.")

    async def send(self, message: str):
        """Send a message to the remote server, handling socket errors gracefully."""
        if not self.ws:
            logger.warning("[ResilientWS] Cannot send message: socket uninitialized.")
            return
        try:
            await self.ws.send(message)
        except Exception as e:
            logger.error(f"[ResilientWS] Error sending message: {e}")
            asyncio.create_task(self.trigger_reconnect())

    async def _connect_with_retry(self):
        """Connects to the server, employing exponential backoff if disconnected."""
        backoff = 2.0
        max_backoff = 60.0
        
        while self.is_running:
            try:
                logger.info(f"[ResilientWS] Connecting to remote endpoint {self.url}...")
                self.ws = await websockets.connect(
                    self.url,
                    extra_headers=self.headers,
                    ping_interval=None, # Disable built-in websockets keepalive so we control it
                    ping_timeout=None
                )
                self.last_pong_time = time.time()
                logger.info(f"[ResilientWS] Successfully connected to {self.url}")
                return
            except Exception as e:
                logger.warning(f"[ResilientWS] Connection failed: {e}. Retrying in {backoff}s...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0, max_backoff)

    async def trigger_reconnect(self):
        """Initiates safe reconnection isolation under lock."""
        async with self._reconnect_lock:
            if self.ws:
                try:
                    await self.ws.close()
                except Exception:
                    pass
                self.ws = None
            
            logger.warning("[ResilientWS] Connection lost or heartbeat timed out. Reconnecting...")
            await self._connect_with_retry()

    async def _heartbeat_loop(self):
        """Actively pings the remote server to detect zombie connections."""
        while self.is_running:
            await asyncio.sleep(self.ping_interval)
            if not self.ws:
                continue

            try:
                if self.ping_message:
                    # 1. Custom string-based ping message
                    logger.debug(f"[ResilientWS] Sending custom heartbeat ping: {self.ping_message}")
                    self.last_ping_time = time.time()
                    await self.send(self.ping_message)
                    
                    # 2. Wait and verify custom pong timeout
                    sent_time = time.time()
                    while time.time() - sent_time < self.pong_timeout:
                        if self.last_pong_time > sent_time:
                            logger.debug("[ResilientWS] Custom heartbeat pong received successfully.")
                            break
                        await asyncio.sleep(0.1)
                    else:
                        logger.warning("[ResilientWS] Custom heartbeat timeout! Zombie socket detected.")
                        asyncio.create_task(self.trigger_reconnect())
                else:
                    # 1. Standard protocol-level ping frame
                    logger.debug("[ResilientWS] Sending protocol heartbeat ping...")
                    pong_waiter = await self.ws.ping()
                    
                    try:
                        # Wait for the pong future to resolve within the timeout window
                        await asyncio.wait_for(pong_waiter, timeout=self.pong_timeout)
                        self.last_pong_time = time.time()
                        logger.debug("[ResilientWS] Protocol heartbeat pong received successfully.")
                    except asyncio.TimeoutError:
                        logger.warning("[ResilientWS] Protocol heartbeat timeout! Zombie socket detected.")
                        asyncio.create_task(self.trigger_reconnect())
            except Exception as e:
                logger.error(f"[ResilientWS] Heartbeat failure: {e}")
                asyncio.create_task(self.trigger_reconnect())

    async def _listen_loop(self):
        """Listens for inbound messages and intercepts custom pongs to refresh last_pong_time."""
        while self.is_running:
            if not self.ws:
                await asyncio.sleep(0.5)
                continue

            try:
                async for message in self.ws:
                    now = time.time()
                    
                    # Intercept custom text-based pong messages
                    if self.pong_message_checker and self.pong_message_checker(message):
                        self.last_pong_time = now
                        logger.debug("[ResilientWS] Custom pong message intercepted.")
                        continue
                    
                    if self.on_message:
                        try:
                            if asyncio.iscoroutinefunction(self.on_message):
                                await self.on_message(message)
                            else:
                                self.on_message(message)
                        except Exception as cb_err:
                            logger.error(f"[ResilientWS] Callback crashed: {cb_err}")
            except Exception as e:
                if self.is_running:
                    logger.warning(f"[ResilientWS] Connection read exception: {e}")
                    asyncio.create_task(self.trigger_reconnect())
                    await asyncio.sleep(1.0)
