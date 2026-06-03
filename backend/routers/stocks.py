from fastapi import APIRouter, HTTPException, Query, Depends
import yfinance as yf
import pandas as pd
import asyncio
from typing import List, Dict, Any, Optional
from services.market_data_service import market_data_service
from core.logger import logger
from utils import safe_json
from auth import get_current_user

router = APIRouter()

def _normalize_ticker(ticker: str) -> str:
    ticker = ticker.upper().strip()
    if ticker.endswith(".NS") or ticker.endswith(".BO"):
        return ticker
    # Add other normalization rules if needed
    return ticker

@router.get("/{ticker}")
async def get_stock_data(ticker: str):
    symbol = _normalize_ticker(ticker)
    try:
        data = await market_data_service.fetch_stock(symbol)
        return safe_json(data)
    except Exception as e:
        logger.error(f"Error fetching stock data for {symbol}: {e}")
        return {
            "ticker": symbol,
            "name": symbol,
            "sector": "Unknown",
            "industry": "Unknown",
            "country": "Unknown",
            "exchange": "Unknown",
            "currency": "USD",
        }

@router.get("/{ticker}/history")
async def get_history(ticker: str, period: str = Query(default="1mo")):
    symbol = _normalize_ticker(ticker)

    is_indian = symbol.endswith(".NS") or symbol.endswith(".BO") or "GS" in symbol or "GB" in symbol
    if is_indian:
        from services.pricing_engine import get_active_upstox_token
        token = await get_active_upstox_token()
        if token:
            try:
                import requests
                from services.pricing_engine import resolve_upstox_keys, to_upstox_instrument_key
                resolved_keys = await resolve_upstox_keys([symbol])
                instrument_key = resolved_keys.get(symbol) or to_upstox_instrument_key(symbol)

                from datetime import date, timedelta
                end_date = date.today()
                if period == "1d": start_date = end_date - timedelta(days=1)
                elif period == "5d": start_date = end_date - timedelta(days=5)
                elif period in ["1mo", "1m"]: start_date = end_date - timedelta(days=30)
                elif period in ["3mo", "3m"]: start_date = end_date - timedelta(days=90)
                elif period in ["6mo", "6m"]: start_date = end_date - timedelta(days=180)
                elif period == "1y": start_date = end_date - timedelta(days=365)
                elif period == "5y": start_date = end_date - timedelta(days=365 * 5)
                else: start_date = end_date - timedelta(days=30)

                to_str = end_date.isoformat()
                from_str = start_date.isoformat()

                url = f"https://api.upstox.com/v2/historical-candle/{instrument_key}/day/{to_str}/{from_str}"
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}"
                }

                loop = asyncio.get_event_loop()
                res = await loop.run_in_executor(None, lambda: requests.get(url, headers=headers, timeout=10))
                if res.status_code == 200:
                    candles = res.json().get("data", {}).get("candles") or []
                    if candles:
                        records = []
                        for c in reversed(candles):
                            date_str = c[0].split("T")[0]
                            records.append({
                                "date": date_str,
                                "time": date_str,
                                "open": float(c[1]),
                                "high": float(c[2]),
                                "low": float(c[3]),
                                "close": float(c[4]),
                                "volume": int(c[5]) if c[5] is not None else None,
                            })
                        return safe_json({"ticker": symbol, "period": period, "history": records, "data": records})
            except Exception as upstox_err:
                logger.warning(f"Upstox history fetch failed for {symbol}: {upstox_err}. Falling back to yfinance.")

    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period, auto_adjust=False)
        if hist.empty:
            raise ValueError(f"Historical data not found for {symbol}")
        
        hist = hist.reset_index()
        records = []
        for _, row in hist.iterrows():
            date_val = row["Date"]
            if hasattr(date_val, "timestamp"):
                if hasattr(date_val, "hour") and date_val.hour == 0 and date_val.minute == 0 and date_val.second == 0:
                    time_val = date_val.strftime("%Y-%m-%d")
                else:
                    time_val = int(date_val.timestamp())
            else:
                time_val = str(date_val)

            records.append({
                "date": date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val),
                "time": time_val,
                "open": float(row["Open"]) if not pd.isna(row["Open"]) else None,
                "high": float(row["High"]) if not pd.isna(row["High"]) else None,
                "low": float(row["Low"]) if not pd.isna(row["Low"]) else None,
                "close": float(row["Close"]) if not pd.isna(row["Close"]) else None,
                "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else None,
            })
        return safe_json({"ticker": symbol, "period": period, "history": records, "data": records})
    except Exception as e:
        logger.warning(f"yfinance history fetch failed for {symbol}: {e}. Trying synthetic historical fallback.")
        try:
            from services.pricing_engine import get_cached_price
            snap = await get_cached_price(symbol)
            base_price = 150.0
            if snap and hasattr(snap, 'last_price') and snap.last_price:
                base_price = float(snap.last_price)
            elif isinstance(snap, dict) and snap.get('price'):
                base_price = float(snap['price'])

            from datetime import datetime, timedelta
            import random
            
            now = datetime.now()
            days_count = 30
            p = period.lower().strip()
            if p == "1d": days_count = 1
            elif p == "5d": days_count = 5
            elif p in ["1mo", "1m"]: days_count = 30
            elif p in ["3mo", "3m"]: days_count = 90
            elif p in ["6mo", "6m"]: days_count = 180
            elif p in ["1y", "12m"]: days_count = 365
            elif p == "5y": days_count = 365 * 5
            else: days_count = 30

            records = []
            current_price = base_price
            for i in range(days_count):
                dt = now - timedelta(days=i)
                date_str = dt.strftime("%Y-%m-%d")
                pct_change = random.normalvariate(0.0005, 0.015)
                prev_price = current_price / (1 + pct_change)
                close_p = current_price
                open_p = prev_price
                high_p = max(close_p, open_p) * (1 + abs(random.normalvariate(0, 0.005)))
                low_p = min(close_p, open_p) * (1 - abs(random.normalvariate(0, 0.005)))
                records.append({
                    "date": date_str,
                    "time": date_str,
                    "open": float(open_p),
                    "high": float(high_p),
                    "low": float(low_p),
                    "close": float(close_p),
                    "volume": random.randint(100000, 1000000)
                })
                current_price = prev_price
            
            return safe_json({"ticker": symbol, "period": period, "history": records, "data": records, "synthetic": True})
        except Exception as synth_err:
            logger.error(f"Synthetic fallback failed for {symbol}: {synth_err}")
            raise HTTPException(status_code=404, detail=f"History not available for {symbol}")

@router.get("/{ticker}/overview")
async def get_stock_overview(ticker: str):
    symbol = _normalize_ticker(ticker)
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        return safe_json(info)
    except Exception as e:
        logger.error(f"Error fetching overview for {symbol}: {e}")
        return {"error": str(e)}
