from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import stocks, portfolio, monte_carlo, backtester, options, risk, signals, market, validate, users, notifications, alerts, strategy_compare
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.alert_service import check_price_alerts
import asyncio
from contextlib import asynccontextmanager

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
