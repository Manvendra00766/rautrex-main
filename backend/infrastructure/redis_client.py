import redis.asyncio as redis
from core.config import settings
from core.logger import logger
from typing import Optional

class RedisClient:
    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def connect(self):
        try:
            from redis.asyncio import BlockingConnectionPool
            pool = BlockingConnectionPool.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=100,
                timeout=5.0,
                socket_timeout=5.0,
                socket_connect_timeout=5.0
            )
            self.redis = redis.Redis(connection_pool=pool)
            # Ping to check connection
            await self.redis.ping()
            logger.info("Connected to Redis successfully with BlockingConnectionPool (max_connections=100).")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None

    async def disconnect(self):
        if self.redis:
            await self.redis.aclose()
            logger.info("Disconnected from Redis.")

    async def get(self, key: str) -> Optional[str]:
        if not self.redis:
            return None
        try:
            return await self.redis.get(key)
        except Exception as e:
            logger.warning(f"Redis get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: str, ttl: int = 60):
        if not self.redis:
            return
        try:
            await self.redis.setex(key, ttl, value)
        except Exception as e:
            logger.warning(f"Redis set error for key {key}: {e}")

    async def delete(self, key: str):
        if not self.redis:
            return
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete error for key {key}: {e}")

redis_client = RedisClient()
