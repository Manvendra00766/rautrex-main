from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
from uuid import uuid4
from core.logger import logger
from schemas.response import error_response

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid4())
        start_time = time.time()
        
        logger.info(f"Incoming Request - ID: {request_id} - {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            logger.info(f"Completed Request - ID: {request_id} - Status: {response.status_code} - Latency: {process_time:.4f}s")
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            return response
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(f"Failed Request - ID: {request_id} - Latency: {process_time:.4f}s - Error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content=error_response(error="Internal Server Error").model_dump()
            )
