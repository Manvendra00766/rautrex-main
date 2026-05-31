import asyncio
import time
from typing import Callable, Any, Coroutine
import httpx
from core.logger import logger

class TokenBucketRateLimiter:
    """
    TokenBucketRateLimiter implements the "API Rate Limits" protection pattern.
    It guarantees a target requests-per-second ceiling using a token-bucket queue
    and automatically intercepts HTTP 429s to lock the queue and execute exponential backoff.
    """
    def __init__(self, rate: float = 5.0, capacity: float = 5.0):
        """
        rate: tokens refilled per second
        capacity: max tokens the bucket can hold
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
        
        # Exponential backoff block state
        self.is_blocked = False
        self.block_until = 0.0

    async def acquire(self):
        """
        Acquire a token. If the bucket is empty, sleep until a token is refilled.
        Respects active exponential backoff blocks from HTTP 429 responses.
        """
        async with self.lock:
            now = time.time()
            if self.is_blocked:
                if now < self.block_until:
                    sleep_dur = self.block_until - now
                    logger.warning(f"[RateLimiter] Queue blocked due to 429. Sleeping for {sleep_dur:.2f}s...")
                    await asyncio.sleep(sleep_dur)
                    now = time.time()
                self.is_blocked = False

            # Refill tokens based on elapsed time
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return

            # Compute wait time for token refill
            needed = 1.0 - self.tokens
            sleep_dur = needed / self.rate
            logger.debug(f"[RateLimiter] Refill delay: waiting {sleep_dur:.4f}s...")
            await asyncio.sleep(sleep_dur)
            
            # Perform a final refill check post-sleep
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate) - 1.0
            self.last_refill = now

    def block_for(self, duration: float):
        """Actively drains tokens and blocks new acquisitions for a duration (backoff period)."""
        self.is_blocked = True
        self.block_until = time.time() + duration
        self.tokens = 0.0
        logger.warning(f"[RateLimiter] Rate limiter locked for {duration:.2f}s.")

    async def execute(self, func: Callable[[], Coroutine[Any, Any, Any]], max_retries: int = 3) -> Any:
        """
        Executes a coroutine func. If it hits an HTTP 429 status code or status error,
        drains the bucket and waits with exponential backoff (2s, 4s, 8s...) before retrying.
        """
        backoff = 2.0
        for attempt in range(1, max_retries + 1):
            await self.acquire()
            try:
                result = await func()
                
                # Support checking both direct httpx.Response status codes
                if hasattr(result, "status_code") and result.status_code == 429:
                    logger.warning(f"[RateLimiter] HTTP 429 detected in response. Retrying (attempt {attempt}/{max_retries})...")
                    self.block_for(backoff)
                    if attempt == max_retries:
                        return result
                    backoff *= 2.0
                    continue
                    
                return result
            except Exception as e:
                is_429 = False
                if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 429:
                    is_429 = True
                elif "429" in str(e) or "too many requests" in str(e).lower():
                    is_429 = True
                
                if is_429:
                    logger.warning(f"[RateLimiter] Exception HTTP 429 caught. Retrying (attempt {attempt}/{max_retries}) after backoff: {e}")
                    self.block_for(backoff)
                    if attempt == max_retries:
                        raise e
                    backoff *= 2.0
                    continue
                else:
                    # Rethrow other failures immediately
                    raise e
