import asyncio
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from schemas.response import error_response
from core.logger import logger

class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout: float = 10.0):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next):
        try:
            response = await asyncio.wait_for(call_next(request), timeout=self.timeout)
            return response
        except asyncio.TimeoutError:
            logger.error(f"Request timeout after {self.timeout}s: {request.method} {request.url.path}")
            return JSONResponse(
                status_code=504,
                content=error_response(error="Request Timeout").model_dump()
            )
