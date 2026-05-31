from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db
from services.market_data_service import market_data_service, get_indices, get_movers, run_screener
from services.ticker_resolver import ticker_resolver_service

router = APIRouter()

@router.get("/resolve")
async def resolve_ticker(query: str, db: AsyncSession = Depends(get_db)):
    try:
        ticker = await ticker_resolver_service.resolve(query, db)
        if not ticker:
            raise HTTPException(status_code=404, detail=f"Could not resolve query '{query}' to a valid ticker.")
        return {"query": query, "resolved_ticker": ticker}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/price")
async def fetch_price(symbol: str):
    try:
        data = await market_data_service.fetch_price(symbol)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/indices")
async def fetch_indices():
    try:
        data = await get_indices()
        return {"indices": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/movers")
async def fetch_movers():
    try:
        data = await get_movers()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/screener")
async def fetch_screener():
    try:
        data = await run_screener()
        return {"results": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from services.ticker_master import ticker_master_service

@router.post("/instruments/sync")
async def lazy_sync_ticker(symbol: str, db: AsyncSession = Depends(get_db)):
    try:
        instrument = await ticker_master_service.lazy_sync_ticker(symbol, db)
        if not instrument:
            raise HTTPException(status_code=404, detail=f"Could not resolve instrument '{symbol}'.")
        return {
            "symbol": instrument.symbol,
            "name": instrument.name,
            "exchange": instrument.exchange,
            "currency": instrument.currency,
            "sector": instrument.sector,
            "asset_type": instrument.asset_type,
            "is_tracked": instrument.is_tracked
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/instruments/sync-all")
async def daily_cron_sync(db: AsyncSession = Depends(get_db)):
    try:
        results = await ticker_master_service.sync_active_instruments(db)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from infrastructure.market_calendar import market_calendar

@router.get("/status")
async def fetch_market_status(symbol: str):
    """Exposes trading session session status, timezone, region, and hours for any symbol."""
    try:
        return market_calendar.get_market_status(symbol)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))