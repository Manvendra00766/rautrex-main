from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from core.exceptions import AppError
from schemas.response import error_response
from core.logger import logger

def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        logger.warning(f"AppError: {exc.message} on {request.url.path}")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(error=exc.message).model_dump()
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled Exception: {str(exc)} on {request.url.path}")
        return JSONResponse(
            status_code=500,
            content=error_response(error="Internal Server Error").model_dump()
        )
