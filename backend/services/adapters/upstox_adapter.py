import asyncio
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
import yfinance as yf

from core.config import settings
from core.logger import logger
from services.pricing_engine import (
    PriceSnapshot, infer_asset_type, SECTOR_MAP,
    get_active_upstox_token, resolve_upstox_keys, to_upstox_instrument_key
)
from .base_adapter import BaseMarketAdapter
from infrastructure.time_sync import offset_calibrated_datetime, offset_calibrated_now

class UpstoxAdapter(BaseMarketAdapter):
    def __init__(self, executor=None):
        self.executor = executor
        self.client = httpx.AsyncClient(timeout=10.0)

    async def fetch_price(self, symbol: str) -> Optional[PriceSnapshot]:
        symbol_upper = symbol.strip().upper()
        token = await get_active_upstox_token()
        
        if not token:
            logger.info(f"[UpstoxAdapter] No active token. Falling back to yfinance for {symbol}")
            return await self._fetch_fallback_yfinance(symbol_upper)

        try:
            resolved_keys = await resolve_upstox_keys([symbol_upper])
            instrument_key = resolved_keys.get(symbol_upper) or to_upstox_instrument_key(symbol_upper)
            
            url = "https://api.upstox.com/v2/market-quote/quotes"
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {token}",
                "X-Request-Timestamp": str(offset_calibrated_now())
            }
            params = {"instrument_key": instrument_key}
            
            response = await self.client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json().get("data") or {}
                quote_data = data.get(instrument_key)
                
                # Check for alternative key mappings
                if not quote_data:
                    colon_key = instrument_key.replace("|", ":") if "|" in instrument_key else instrument_key
                    quote_data = data.get(colon_key)
                if not quote_data:
                    for k, v in data.items():
                        if v.get("instrument_token") == instrument_key:
                            quote_data = v
                            break
                if not quote_data and data:
                    quote_data = next(iter(data.values()))

                if quote_data:
                    last_price = float(quote_data.get("last_price") or quote_data.get("last_traded_price") or 0.0)
                    close_price = float(quote_data.get("close") or quote_data.get("ohlc", {}).get("close") or last_price)
                    change_amount = last_price - close_price
                    change_percent = (change_amount / close_price * 100.0) if close_price > 0 else 0.0
                    
                    return PriceSnapshot(
                        symbol=symbol_upper,
                        name=quote_data.get("symbol") or symbol_upper,
                        asset_type="equity",
                        currency="INR",
                        exchange=instrument_key.split("|")[0] if "|" in instrument_key else (instrument_key.split(":")[0] if ":" in instrument_key else "NSE"),
                        sector="Government Securities" if ("GS" in symbol_upper or "GB" in symbol_upper) else SECTOR_MAP.get(symbol_upper, "Indian Equity"),
                        country="IN",
                        market_cap=None,
                        previous_close=close_price,
                        last_price=last_price,
                        change_amount=change_amount,
                        change_percent=change_percent,
                        volume=int(quote_data.get("volume") or 0) if quote_data.get("volume") else None,
                        source="Upstox",
                        fetched_at=offset_calibrated_datetime(),
                        raw=quote_data,
                    )
            logger.warning(f"[UpstoxAdapter] API failed (status {response.status_code}): {response.text}")
            return await self._fetch_fallback_yfinance(symbol_upper)
        except Exception as e:
            logger.error(f"[UpstoxAdapter] Error fetching Upstox price for {symbol_upper}: {e}")
            return await self._fetch_fallback_yfinance(symbol_upper)

    async def _fetch_fallback_yfinance(self, symbol: str) -> Optional[PriceSnapshot]:
        """Fetch Indian asset details using yfinance (e.g. RELIANCE.NS)."""
        loop = asyncio.get_event_loop()
        def fetch():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d", auto_adjust=False)
                if hist.empty:
                    return None
                
                info = {}
                try:
                    info = ticker.info or {}
                except Exception:
                    pass
                
                closes = hist["Close"].dropna()
                if closes.empty:
                    return None
                
                last_price = float(closes.iloc[-1])
                prev_close = float(closes.iloc[-2]) if len(closes) > 1 else float(info.get("previousClose") or last_price)
                
                change_amount = last_price - prev_close
                change_percent = (change_amount / prev_close * 100.0) if prev_close else 0.0
                
                return PriceSnapshot(
                    symbol=symbol,
                    name=info.get("longName") or info.get("shortName") or symbol,
                    asset_type=infer_asset_type(symbol, info),
                    currency=info.get("currency") or "INR",
                    exchange=info.get("exchange") or "NSE",
                    sector=info.get("sector") or SECTOR_MAP.get(symbol, "Indian Equity"),
                    country=info.get("country") or "IN",
                    market_cap=info.get("marketCap"),
                    previous_close=prev_close,
                    last_price=last_price,
                    change_amount=change_amount,
                    change_percent=change_percent,
                    volume=int(hist["Volume"].dropna().iloc[-1]) if "Volume" in hist else None,
                    source="Upstox (yfinance fallback)",
                    fetched_at=offset_calibrated_datetime(),
                    raw={},
                    is_fallback=True
                )
            except Exception as e:
                logger.error(f"[UpstoxAdapter] yfinance fallback failed for {symbol}: {e}")
                return None

        return await loop.run_in_executor(self.executor, fetch)

    async def fetch_history(self, symbol: str, period: str = "1mo") -> List[Dict[str, Any]]:
        # Upstox history fetcher
        token = await get_active_upstox_token()
        symbol_upper = symbol.strip().upper()
        
        if token:
            try:
                resolved_keys = await resolve_upstox_keys([symbol_upper])
                instrument_key = resolved_keys.get(symbol_upper) or to_upstox_instrument_key(symbol_upper)
                
                end_date = datetime.today().date()
                if period == "1d": start_date = end_date - asyncio.timedelta(days=1)
                elif period == "5d": start_date = end_date - asyncio.timedelta(days=5)
                elif period in ["1mo", "1m"]: start_date = end_date - asyncio.timedelta(days=30)
                elif period in ["3mo", "3m"]: start_date = end_date - asyncio.timedelta(days=90)
                elif period in ["6mo", "6m"]: start_date = end_date - asyncio.timedelta(days=180)
                elif period == "1y": start_date = end_date - asyncio.timedelta(days=365)
                else: start_date = end_date - asyncio.timedelta(days=30)
                
                url = f"https://api.upstox.com/v2/historical-candle/{instrument_key}/day/{end_date.isoformat()}/{start_date.isoformat()}"
                headers = {
                    "Accept": "application/json",
                    "Authorization": f"Bearer {token}"
                }
                
                response = await self.client.get(url, headers=headers)
                if response.status_code == 200:
                    candles = response.json().get("data", {}).get("candles") or []
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
                            "volume": int(c[5]) if c[5] is not None else 0,
                        })
                    return records
            except Exception as e:
                logger.warning(f"[UpstoxAdapter] History failed, falling back to yfinance: {e}")
                
        # yfinance fallback
        loop = asyncio.get_event_loop()
        def fetch():
            try:
                ticker = yf.Ticker(symbol_upper)
                hist = ticker.history(period=period, auto_adjust=False)
                if hist.empty:
                    return []
                records = []
                for idx, row in hist.iterrows():
                    date_str = idx.strftime('%Y-%m-%d')
                    records.append({
                        "date": date_str,
                        "time": date_str,
                        "open": float(row["Open"]),
                        "high": float(row["High"]),
                        "low": float(row["Low"]),
                        "close": float(row["Close"]),
                        "volume": int(row["Volume"]) if "Volume" in row else 0,
                    })
                return records
            except Exception as e:
                logger.error(f"[UpstoxAdapter] yfinance history failed for {symbol_upper}: {e}")
                return []
        return await loop.run_in_executor(self.executor, fetch)

    async def fetch_batch(self, symbols: List[str]) -> Dict[str, Optional[PriceSnapshot]]:
        if not symbols:
            return {}
        tasks = [self.fetch_price(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = {}
        for s, res in zip(symbols, results):
            if isinstance(res, Exception) or res is None:
                output[s] = None
            else:
                output[s] = res
        return output
