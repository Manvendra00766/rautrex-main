import asyncio
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import httpx
import yfinance as yf

from core.config import settings
from core.logger import logger
from services.pricing_engine import PriceSnapshot
from .base_adapter import BaseMarketAdapter
from infrastructure.time_sync import offset_calibrated_datetime, offset_calibrated_now

# Maps standard commodity/futures symbols to OANDA instrument identifiers
COMMODITY_MAP = {
    "GC=F": "XAU_USD",    # Gold Futures -> Gold CFD
    "CL=F": "WTICO_USD",  # Crude Oil Futures -> WTI Crude CFD
    "SI=F": "XAG_USD",    # Silver Futures -> Silver CFD
    "NG=F": "NATGAS_USD", # Natural Gas -> Nat Gas CFD
    "BZ=F": "BCO_USD",    # Brent Crude -> Brent CFD
    # Direct CFD fallbacks
    "XAU_USD": "XAU_USD",
    "XAG_USD": "XAG_USD",
    "WTICO_USD": "WTICO_USD",
    "BCO_USD": "BCO_USD",
}

REVERSE_MAP = {v: k for k, v in COMMODITY_MAP.items()}

class OandaAdapter(BaseMarketAdapter):
    def __init__(self, executor=None):
        self.executor = executor
        self.api_key = (settings.OANDA_API_KEY or "").strip('"').strip("'")
        self.account_id = (settings.OANDA_ACCOUNT_ID or "").strip('"').strip("'")
        self.base_url = (settings.OANDA_BASE_URL or "").strip('"').strip("'")
        self.client = httpx.AsyncClient(timeout=10.0)

    def _is_configured(self) -> bool:
        return bool(self.api_key and self.account_id and self.base_url)

    async def fetch_price(self, symbol: str) -> Optional[PriceSnapshot]:
        symbol_upper = symbol.strip().upper()
        oanda_instrument = COMMODITY_MAP.get(symbol_upper, symbol_upper)

        if not self._is_configured():
            logger.info(f"[OandaAdapter] OANDA credentials missing. Falling back to yfinance for {symbol_upper}")
            return await self._fetch_fallback_yfinance(symbol_upper)

        try:
            # Endpoint for latest pricing: /v3/accounts/{account_id}/pricing
            url = f"{self.base_url}/v3/accounts/{self.account_id}/pricing"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-Request-Timestamp": str(offset_calibrated_now())
            }
            params = {"instruments": oanda_instrument}
            
            response = await self.client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json() or {}
                prices = data.get("prices") or []
                if not prices:
                    raise ValueError(f"No prices returned from OANDA for {oanda_instrument}")
                
                price_data = prices[0]
                # In OANDA, bids/asks are returned. The closeoutBid or closeoutAsk can be averaged
                bids = price_data.get("bids") or []
                asks = price_data.get("asks") or []
                
                bid_price = float(bids[0].get("price")) if bids else float(price_data.get("closeoutBid", 0))
                ask_price = float(asks[0].get("price")) if asks else float(price_data.get("closeoutAsk", 0))
                last_price = (bid_price + ask_price) / 2.0
                
                # OANDA doesn't return daily change or previous close, so we enrich with yfinance close
                prev_close = last_price
                try:
                    ticker = yf.Ticker(symbol_upper)
                    hist = ticker.history(period="2d")
                    if not hist.empty and len(hist) >= 2:
                        prev_close = float(hist["Close"].iloc[-2])
                except Exception:
                    pass
                
                change_amount = last_price - prev_close
                change_percent = (change_amount / prev_close * 100.0) if prev_close else 0.0

                return PriceSnapshot(
                    symbol=symbol_upper,
                    name=symbol_upper.replace("=F", " Commodity"),
                    asset_type="commodity",
                    currency="USD",
                    exchange="OANDA",
                    sector="Commodities",
                    country="Global",
                    market_cap=None,
                    previous_close=prev_close,
                    last_price=last_price,
                    change_amount=change_amount,
                    change_percent=change_percent,
                    volume=None,
                    source="OANDA",
                    fetched_at=offset_calibrated_datetime(),
                    raw=price_data
                )
            else:
                logger.warning(f"[OandaAdapter] API error {response.status_code}: {response.text}")
                return await self._fetch_fallback_yfinance(symbol_upper)
        except Exception as e:
            logger.error(f"[OandaAdapter] Error fetching OANDA price for {symbol_upper}: {e}")
            return await self._fetch_fallback_yfinance(symbol_upper)

    async def _fetch_fallback_yfinance(self, symbol: str) -> Optional[PriceSnapshot]:
        """Fetch commodity using yfinance (e.g. GC=F)."""
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
                    asset_type="commodity",
                    currency=info.get("currency") or "USD",
                    exchange=info.get("exchange") or "NYMEX",
                    sector="Commodities",
                    country="Global",
                    market_cap=None,
                    previous_close=prev_close,
                    last_price=last_price,
                    change_amount=change_amount,
                    change_percent=change_percent,
                    volume=int(hist["Volume"].dropna().iloc[-1]) if "Volume" in hist else None,
                    source="OANDA (yfinance fallback)",
                    fetched_at=offset_calibrated_datetime(),
                    raw={},
                    is_fallback=True
                )
            except Exception as e:
                logger.error(f"[OandaAdapter] yfinance fallback failed for {symbol}: {e}")
                return None

        return await loop.run_in_executor(self.executor, fetch)

    async def fetch_history(self, symbol: str, period: str = "1mo") -> List[Dict[str, Any]]:
        # OANDA historical data fallback to yfinance
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
                logger.error(f"[OandaAdapter] yfinance history failed for commodity {symbol}: {e}")
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
