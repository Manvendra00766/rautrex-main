from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from core.exceptions import AppError
from schemas.response import error_response
from core.logger import logger

def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        details = {}
        for err in exc.errors():
            loc = err.get("loc", [])
            # Extract the actual field name (e.g. ('body', 'ticker') -> 'ticker')
            field = str(loc[-1]) if loc else "field"
            # Standardize message
            msg = err.get("msg", "Invalid value")
            # Clean up the Pydantic type prefix if present
            if msg.startswith("Value error, "):
                msg = msg.replace("Value error, ", "", 1)
            details[field] = msg
            
        logger.warning(f"Validation failed on {request.url.path}: {details}")
        
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": "Validation failed",
                "details": details
            }
        )

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
