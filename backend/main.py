from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)

# Import core modules
from core.config import settings
from core.logger import setup_logging, logger
from core.exceptions import AppError
from middleware.logging_middleware import LoggingMiddleware
from middleware.timeout_middleware import TimeoutMiddleware
from middleware.exception_handler import setup_exception_handlers
from infrastructure.redis_client import redis_client
from services.market_data_service import market_data_service
from services.alert_service import check_price_alerts
import json
from utils import safe_json

# Import routers
from routers import stocks, portfolio, monte_carlo, backtester, options, risk, signals, market, validate, users, notifications, alerts, strategy_compare, dcf_router, screener_router, paper_trading_router, report_router, onboarding
from websocket_app.routes import router as ws_router

# Setup structured logging
setup_logging()

class JSONSanitizerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Exclude endpoints that handle binary data or predictions
        path = request.url.path
        if path.endswith("/predict") or "/report" in path or "/export" in path:
             return await call_next(request)
             
        response = await call_next(request)
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            try:
                data = json.loads(body)
                sanitized_data = safe_json(data)
                new_content = json.dumps(sanitized_data).encode("utf-8")
                headers = dict(response.headers)
                headers.pop("content-length", None)
                return Response(content=new_content, status_code=response.status_code, headers=headers, media_type="application/json")
            except Exception:
                headers = dict(response.headers)
                headers.pop("content-length", None)
                return Response(content=body, status_code=response.status_code, headers=headers, media_type="application/json")
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Redis connection
    await redis_client.connect()
    
    # Startup: Background Workers (Streaming Engine & Scheduler)
    from workers.scheduler import worker
    worker.start()
    
    logger.info("Application startup complete.")
    yield
    
    # Shutdown
    logger.info("Application shutting down...")
    worker.stop()
    await market_data_service.close()
    await redis_client.disconnect()

import os
import uuid
import sentry_sdk
from prometheus_fastapi_instrumentator import Instrumentator

sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        # Also bind to loguru context if needed
        with logger.contextualize(request_id=request_id):
            response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Setup Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Add Middlewares
app.add_middleware(RequestIdMiddleware)
app.add_middleware(JSONSanitizerMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(TimeoutMiddleware, timeout=60.0)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
setup_exception_handlers(app)

# Health check
@app.get("/health")
@app.get("/api/v1/health")
async def health_check():
    return {"status": "ok", "service": "rautrex-backend", "environment": settings.ENVIRONMENT}

# Include routers
app.include_router(stocks.router, prefix="/api/v1/stocks", tags=["Stocks"])
app.include_router(market.router, prefix="/api/v1/market", tags=["Market Data"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
app.include_router(monte_carlo.router, prefix="/api/v1/monte-carlo", tags=["Monte Carlo"])
app.include_router(backtester.router, prefix="/api/v1/backtest", tags=["Backtester"])
app.include_router(strategy_compare.router, prefix="/api/v1/compare", tags=["Strategy Compare"])
app.include_router(options.router, prefix="/api/v1/options", tags=["Options Pricing"])
app.include_router(risk.router, prefix="/api/v1/risk", tags=["Risk Analytics"])
app.include_router(signals.router, prefix="/api/v1/signals", tags=["ML Signals"])
app.include_router(validate.router, prefix="/api/v1/validate", tags=["Validation"])
app.include_router(dcf_router.router, prefix="/api/v1/dcf", tags=["DCF Valuation"])
app.include_router(screener_router.router, prefix="/api/v1/screener", tags=["Stock Screener"])
app.include_router(paper_trading_router.router, prefix="/api/v1/paper", tags=["Paper Trading"])
app.include_router(report_router.router)
app.include_router(notifications.router)
app.include_router(alerts.router)
app.include_router(users.router)
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])
app.include_router(onboarding.router, prefix="/api/v1/onboarding", tags=["Onboarding"])

# Websocket router
app.include_router(ws_router, tags=["Websockets"])
