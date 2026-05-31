import asyncio
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
import yfinance as yf

from core.config import settings
from core.logger import logger
from services.pricing_engine import PriceSnapshot, infer_asset_type, SECTOR_MAP
from .base_adapter import BaseMarketAdapter
from infrastructure.time_sync import offset_calibrated_datetime, offset_calibrated_now

class AlpacaAdapter(BaseMarketAdapter):
    def __init__(self, executor=None):
        self.executor = executor
        self.api_key_id = (settings.ALPACA_API_KEY_ID or "").strip('"').strip("'")
        self.secret_key = (settings.ALPACA_SECRET_KEY or "").strip('"').strip("'")
        # Paper data API URL: https://data.alpaca.markets/v2
        # Or standard: https://data.alpaca.markets/v2
        self.base_url = "https://data.alpaca.markets/v2"
        self.client = httpx.AsyncClient(timeout=10.0)

    def _is_configured(self) -> bool:
        return bool(self.api_key_id and self.secret_key)

    async def fetch_price(self, symbol: str) -> Optional[PriceSnapshot]:
        symbol = symbol.strip().upper()
        if not self._is_configured():
            logger.info(f"[AlpacaAdapter] Keys missing. Falling back to yfinance for {symbol}")
            return await self._fetch_fallback_yfinance(symbol)

        try:
            # Let's request the snapshot endpoint, which has latest trade and daily bar
            url = f"{self.base_url}/stocks/snapshots"
            headers = {
                "APCA-API-KEY-ID": self.api_key_id,
                "APCA-API-SECRET-KEY": self.secret_key,
                "Accept": "application/json",
                "X-Request-Timestamp": str(offset_calibrated_now())
            }
            params = {"symbols": symbol}
            
            response = await self.client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json() or {}
                snap = data.get(symbol) or {}
                
                # Extract latest trade or latest bar
                latest_trade = snap.get("latestTrade") or {}
                latest_bar = snap.get("latestBar") or {}
                prev_daily_bar = snap.get("minuteBar") or latest_bar # backup
                
                last_price = latest_trade.get("p") or latest_bar.get("c")
                if last_price is None:
                    raise ValueError(f"No price found in Alpaca response for {symbol}")
                
                # Fetch details using yfinance info in background or fallback
                # Since Alpaca only returns raw ticks, we enrich it
                prev_close = latest_bar.get("o") or last_price # approximate or pull from yfinance if needed
                
                # For high fidelity, we can run yfinance info cache fetch
                name = symbol
                sector = SECTOR_MAP.get(symbol, "US Equity")
                
                change_amount = last_price - prev_close
                change_percent = (change_amount / prev_close * 100.0) if prev_close else 0.0
                
                return PriceSnapshot(
                    symbol=symbol,
                    name=name,
                    asset_type="equity",
                    currency="USD",
                    exchange="NASDAQ" if len(symbol) == 4 else "NYSE",
                    sector=sector,
                    country="US",
                    market_cap=None,
                    previous_close=float(prev_close),
                    last_price=float(last_price),
                    change_amount=float(change_amount),
                    change_percent=float(change_percent),
                    volume=latest_bar.get("v") or 0,
                    source="Alpaca",
                    fetched_at=offset_calibrated_datetime(),
                    raw=snap
                )
            else:
                logger.warning(f"[AlpacaAdapter] API error {response.status_code}: {response.text}")
                return await self._fetch_fallback_yfinance(symbol)
        except Exception as e:
            logger.error(f"[AlpacaAdapter] Error fetching {symbol}: {e}")
            return await self._fetch_fallback_yfinance(symbol)

    async def _fetch_fallback_yfinance(self, symbol: str) -> Optional[PriceSnapshot]:
        """High-fidelity fallback using yfinance to fetch US equities."""
        loop = asyncio.get_event_loop()
        def fetch():
            try:
                ticker = yf.Ticker(symbol)
                # Fetch recent history to compute price and close
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
                    currency=info.get("currency") or "USD",
                    exchange=info.get("exchange") or "NASDAQ",
                    sector=info.get("sector") or SECTOR_MAP.get(symbol, "Information Technology"),
                    country=info.get("country") or "US",
                    market_cap=info.get("marketCap"),
                    previous_close=prev_close,
                    last_price=last_price,
                    change_amount=change_amount,
                    change_percent=change_percent,
                    volume=int(hist["Volume"].dropna().iloc[-1]) if "Volume" in hist else None,
                    source="Alpaca (yfinance fallback)",
                    fetched_at=offset_calibrated_datetime(),
                    raw={
                        "trailingPE": info.get("trailingPE"),
                        "marketCap": info.get("marketCap"),
                    },
                    is_fallback=True
                )
            except Exception as e:
                logger.error(f"[AlpacaAdapter] yfinance fallback failed for {symbol}: {e}")
                return None

        return await loop.run_in_executor(self.executor, fetch)

    async def fetch_history(self, symbol: str, period: str = "1mo") -> List[Dict[str, Any]]:
        # For history, use the same high-fidelity fallback because Alpaca free tier historical bars are highly limited or delayed
        loop = asyncio.get_event_loop()
        def fetch():
            try:
                ticker = yf.Ticker(symbol)
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
                logger.error(f"[AlpacaAdapter] History fetch failed for {symbol}: {e}")
                return []
        return await loop.run_in_executor(self.executor, fetch)

    async def fetch_batch(self, symbols: List[str]) -> Dict[str, Optional[PriceSnapshot]]:
        if not symbols:
            return {}
        
        # Concurrently fetch symbols
        tasks = [self.fetch_price(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        output = {}
        for s, res in zip(symbols, results):
            if isinstance(res, Exception) or res is None:
                output[s] = None
            else:
                output[s] = res
        return output
