from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from services.market_data_service import search_tickers, get_quote, get_history, get_fundamentals, get_news, get_info
import asyncio

router = APIRouter()

@router.get("/search")
async def search_stock(q: str = Query(..., description="Ticker or company name"), exchange: str = "all"):
    try:
        results = await search_tickers(q, exchange)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{ticker}/quote")
async def fetch_quote(ticker: str):
    data = await get_quote(ticker)
    if not data: raise HTTPException(status_code=404, detail="Data not found")
    return data

@router.get("/{ticker}/history")
async def fetch_history(ticker: str, period: str = "1mo"):
    data = await get_history(ticker, period)
    return {"ticker": ticker, "data": data}

@router.get("/{ticker}/fundamentals")
async def fetch_fundamentals(ticker: str):
    data = await get_fundamentals(ticker)
    return data

@router.get("/{ticker}/news")
async def fetch_news(ticker: str):
    data = await get_news(ticker)
    return {"news": data}

@router.get("/{ticker}/info")
async def fetch_info(ticker: str):
    data = await get_info(ticker)
    return data