from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from routers import stocks, portfolio, monte_carlo, backtester, options, risk, signals, market, validate, users, notifications, alerts, strategy_compare
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.alert_service import check_price_alerts
import asyncio
import json
from utils import safe_json
from contextlib import asynccontextmanager

class JSONSanitizerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Only process JSON responses
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            body = b""
            async for chunk in response.body_iterator:
                body += chunk
            
            try:
                # Attempt to parse, sanitize, and re-serialize
                data = json.loads(body)
                sanitized_data = safe_json(data)
                new_content = json.dumps(sanitized_data).encode("utf-8")
                
                # Create new response with sanitized content
                return Response(
                    content=new_content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type="application/json"
                )
            except Exception as e:
                # If parsing fails, return original body (it might already be sanitized or not JSON)
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type="application/json"
                )
        
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start APScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_price_alerts, 'interval', minutes=5)
    scheduler.start()
    yield
    # Shutdown
    scheduler.shutdown()

app = FastAPI(title="RAUTREX API", version="1.0.0", lifespan=lifespan)

# Add JSON Sanitizer Middleware
app.add_middleware(JSONSanitizerMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://rautrex.vercel.app", # Potential production URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"status": "ok"}

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
app.include_router(notifications.router)
app.include_router(alerts.router)
app.include_router(users.router)

@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy"}
