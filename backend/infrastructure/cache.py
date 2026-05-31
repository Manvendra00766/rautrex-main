import functools
import json
from typing import Callable, Any
from fastapi.encoders import jsonable_encoder
from .redis_client import redis_client
from core.logger import logger

def cache_response(ttl: int = 60, prefix: str = "cache"):
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create a cache key based on function name and arguments
            key_parts = [prefix, func.__name__]
            if args:
                key_parts.extend([str(a) for a in args])
            if kwargs:
                key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_value = await redis_client.get(cache_key)
            if cached_value:
                logger.debug(f"Cache hit for key: {cache_key}")
                return json.loads(cached_value)
            
            logger.debug(f"Cache miss for key: {cache_key}")
            # Execute function
            result = await func(*args, **kwargs)
            
            # Save to cache if successful
            if result is not None:
                # Custom JSON serialization using FastAPI's jsonable_encoder to support
                # SQLAlchemy models, datetimes, decimals, and custom enums.
                try:
                    serialized = json.dumps(jsonable_encoder(result))
                    await redis_client.set(cache_key, serialized, ttl)
                except Exception as e:
                    logger.warning(f"Could not serialize result for cache key: {cache_key}. Error: {e}")
                    
            return result
        return wrapper
    return decorator
