import asyncio
from typing import List, Dict, Any, Optional
import httpx
import yfinance as yf

from core.config import settings
from core.logger import logger
from services.pricing_engine import PriceSnapshot, infer_asset_type, SECTOR_MAP
from .base_adapter import BaseMarketAdapter
from infrastructure.time_sync import offset_calibrated_datetime

class TwelveDataAdapter(BaseMarketAdapter):
    def __init__(self, executor=None):
        self.executor = executor
        self.api_key = (getattr(settings, "TWELVEDATA_API_KEY", None) or "").strip('"').strip("'")
        self.base_url = "https://api.twelvedata.com"
        self.client = httpx.AsyncClient(timeout=10.0)

    def _is_configured(self) -> bool:
        return bool(self.api_key)

    async def fetch_price(self, symbol: str) -> Optional[PriceSnapshot]:
        symbol = symbol.strip().upper()
        if not self._is_configured():
            logger.info(f"[TwelveDataAdapter] Keys missing. Falling back to yfinance for {symbol}")
            return await self._fetch_fallback_yfinance(symbol)

        try:
            url = f"{self.base_url}/quote"
            # Map standard Yahoo symbols to TwelveData forex/commodity symbols
            mapped_symbol = symbol
            if symbol in ["GC=F", "GOLD"]: mapped_symbol = "XAU/USD"
            elif symbol == "SI=F": mapped_symbol = "XAG/USD"
            elif symbol == "CL=F": mapped_symbol = "XTI/USD"
            
            params = {
                "symbol": mapped_symbol,
                "apikey": self.api_key
            }
            
            response = await self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if "code" in data and data["code"] >= 400:
                    logger.warning(f"[TwelveDataAdapter] API error: {data}")
                    return await self._fetch_fallback_yfinance(symbol)
                
                last_price = float(data.get("close") or data.get("previous_close") or 0)
                prev_close = float(data.get("previous_close") or last_price)
                
                change_amount = float(data.get("change") or (last_price - prev_close))
                change_percent = float(data.get("percent_change") or (change_amount / prev_close * 100.0 if prev_close else 0.0))
                
                return PriceSnapshot(
                    symbol=symbol,
                    name=data.get("name") or symbol,
                    asset_type="commodity",
                    currency=data.get("currency") or "USD",
                    exchange=data.get("exchange") or "Forex",
                    sector="Commodity",
                    country="Global",
                    market_cap=None,
                    previous_close=prev_close,
                    last_price=last_price,
                    change_amount=change_amount,
                    change_percent=change_percent,
                    volume=int(data.get("volume") or 0),
                    source="TwelveData",
                    fetched_at=offset_calibrated_datetime(),
                    raw=data
                )
            else:
                return await self._fetch_fallback_yfinance(symbol)
        except Exception as e:
            logger.error(f"[TwelveDataAdapter] Error fetching {symbol}: {e}")
            return await self._fetch_fallback_yfinance(symbol)

    async def _fetch_fallback_yfinance(self, symbol: str) -> Optional[PriceSnapshot]:
        loop = asyncio.get_event_loop()
        def fetch():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d", auto_adjust=False)
                if hist.empty: return None
                
                info = {}
                try: info = ticker.info or {}
                except Exception: pass
                
                closes = hist["Close"].dropna()
                if closes.empty: return None
                
                last_price = float(closes.iloc[-1])
                prev_close = float(closes.iloc[-2]) if len(closes) > 1 else float(info.get("previousClose") or last_price)
                
                change_amount = last_price - prev_close
                change_percent = (change_amount / prev_close * 100.0) if prev_close else 0.0
                
                return PriceSnapshot(
                    symbol=symbol,
                    name=info.get("longName") or info.get("shortName") or symbol,
                    asset_type="commodity",
                    currency=info.get("currency") or "USD",
                    exchange=info.get("exchange") or "NYMEX",
                    sector="Commodity",
                    country="Global",
                    market_cap=info.get("marketCap"),
                    previous_close=prev_close,
                    last_price=last_price,
                    change_amount=change_amount,
                    change_percent=change_percent,
                    volume=int(hist["Volume"].dropna().iloc[-1]) if "Volume" in hist else None,
                    source="TwelveData (yfinance fallback)",
                    fetched_at=offset_calibrated_datetime(),
                    raw={"marketCap": info.get("marketCap")},
                    is_fallback=True
                )
            except Exception as e:
                return None
        return await loop.run_in_executor(self.executor, fetch)

    async def fetch_history(self, symbol: str, period: str = "1mo") -> List[Dict[str, Any]]:
        # Using Yfinance as high-fidelity fallback for historical bars because TwelveData free tier is limited
        loop = asyncio.get_event_loop()
        def fetch():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period, auto_adjust=False)
                if hist.empty: return []
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
                return []
        return await loop.run_in_executor(self.executor, fetch)

    async def fetch_batch(self, symbols: List[str]) -> Dict[str, Optional[PriceSnapshot]]:
        if not symbols: return {}
        tasks = [self.fetch_price(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        output = {}
        for s, res in zip(symbols, results):
            if isinstance(res, Exception) or res is None: output[s] = None
            else: output[s] = res
        return output
