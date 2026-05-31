import asyncio
import time
from enum import Enum
from typing import Dict, Any, List
import httpx
from core.logger import logger
from core.exceptions import MarketDataError
from infrastructure.cache import cache_response
from infrastructure.rate_limiter import TokenBucketRateLimiter

from services.adapters.alpaca_adapter import AlpacaAdapter
from services.adapters.upstox_adapter import UpstoxAdapter
from services.adapters.twelvedata_adapter import TwelveDataAdapter

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(f"Circuit Breaker TRIPPED (OPEN). Threshold: {self.failure_threshold}")

    def record_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit Breaker transitioned to HALF_OPEN. Attempting recovery.")
                return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            return True
        
        return False

class MarketDataService:
    def __init__(self):
        self.limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
        self.timeout = httpx.Timeout(10.0, connect=5.0)
        self.client = httpx.AsyncClient(
            limits=self.limits,
            timeout=self.timeout
        )
        # Dedicated thread pool strictly for slow, blocking yfinance fallback lookups
        from concurrent.futures import ThreadPoolExecutor
        self.fallback_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="market_fallback")

        # Concrete adapters with isolated resource thread limits
        self.alpaca_adapter = AlpacaAdapter(executor=self.fallback_executor)
        self.upstox_adapter = UpstoxAdapter(executor=self.fallback_executor)
        self.twelvedata_adapter = TwelveDataAdapter(executor=self.fallback_executor)
        
        self.circuit_breaker = CircuitBreaker()
        self.rate_limiter = TokenBucketRateLimiter(rate=5.0, capacity=5.0)

    async def close(self):
        await self.client.aclose()
        await self.alpaca_adapter.client.aclose()
        await self.upstox_adapter.client.aclose()
        await self.twelvedata_adapter.client.aclose()
        # Shutdown the thread pool executor cleanly
        self.fallback_executor.shutdown(wait=False)

    def _get_adapter(self, symbol: str):
        symbol_upper = symbol.strip().upper()
        
        # Rule A: Indian Stocks (.NS, .BO, or specific identifiers)
        if symbol_upper.endswith(".NS") or symbol_upper.endswith(".BO") or "GS" in symbol_upper or "GB" in symbol_upper:
            return self.upstox_adapter
            
        # Rule B: Commodities (matching GC=F, CL=F, SI=F, NG=F, BZ=F or CFDs)
        commodities = {"GC=F", "CL=F", "SI=F", "NG=F", "BZ=F", "XAU_USD", "XAG_USD", "WTICO_USD", "BCO_USD", "GOLD"}
        if symbol_upper in commodities:
            return self.twelvedata_adapter
            
        # Rule C: Default US equities
        return self.alpaca_adapter

    async def fetch_price(self, symbol: str) -> Dict[str, Any]:
        """High-level fetch with circuit breaker, rate limiter, intelligent routing, and fallback adapters."""
        if not self.circuit_breaker.can_execute():
            logger.warning(f"Circuit Breaker is OPEN. Skipping fetch for {symbol}.")
            return await self._get_stale_data_fallback(symbol)

        adapter = self._get_adapter(symbol)
        try:
            async def perform_fetch():
                return await adapter.fetch_price(symbol)
            snapshot = await self.rate_limiter.execute(perform_fetch)
            if snapshot:
                # FIXED: Check if the price was fetched via fallback to properly trip the circuit breaker
                if getattr(snapshot, "is_fallback", False):
                    logger.warning(f"Market data fetched via fallback for {symbol}. Recording failure on circuit breaker.")
                    self.circuit_breaker.record_failure()
                else:
                    self.circuit_breaker.record_success()
                return {
                    "ticker": snapshot.symbol,
                    "price": snapshot.last_price,
                    "regularMarketPrice": snapshot.last_price,
                    "previous_close": snapshot.previous_close,
                    "change_amount": snapshot.change_amount,
                    "change_percent": snapshot.change_percent,
                    "volume": snapshot.volume,
                    "name": snapshot.name,
                    "currency": snapshot.currency,
                    "source": snapshot.source,
                    "timestamp": snapshot.fetched_at.timestamp()
                }
            else:
                raise MarketDataError(f"Adapter {adapter.__class__.__name__} failed to fetch symbol {symbol}")
        except Exception as e:
            logger.warning(f"Adapter failed for {symbol}: {e}. Tripping circuit breaker action.")
            self.circuit_breaker.record_failure()
            return await self._get_stale_data_fallback(symbol)

    async def _get_stale_data_fallback(self, symbol: str) -> Dict:
        """Final fallback: returns structured empty data to prevent frontend crash."""
        logger.info(f"Returning graceful fallback data for {symbol}")
        return {
            "ticker": symbol,
            "price": 0.0,
            "status": "stale",
            "error": "Market data providers unavailable",
            "timestamp": time.time()
        }

    @cache_response(ttl=60, prefix="market:stock")
    async def fetch_stock(self, symbol: str) -> Dict[str, Any]:
        return await self.fetch_price(symbol)

    async def fetch_batch(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Fetch prices for multiple symbols concurrently with a semaphore limit to prevent provider rate limiting."""
        if not symbols:
            return {}
            
        sem = asyncio.Semaphore(10)
        
        async def fetch_with_semaphore(symbol: str) -> Dict[str, Any]:
            async with sem:
                try:
                    return await self.fetch_price(symbol)
                except Exception as e:
                    logger.error(f"Error fetching batch price for {symbol}: {e}")
                    return await self._get_stale_data_fallback(symbol)
                    
        tasks = {symbol: fetch_with_semaphore(symbol) for symbol in symbols}
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        
        batch_results = {}
        for symbol, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                logger.error(f"Batch task for {symbol} generated exception: {result}")
                batch_results[symbol] = await self._get_stale_data_fallback(symbol)
            else:
                batch_results[symbol] = result
                
        return batch_results

    @cache_response(ttl=120, prefix="market:indices")
    async def get_indices(self) -> List[Dict]:
        """Fetch index data dynamically from yfinance with static fallback."""
        default_indices = [
            {"ticker": "^GSPC", "name": "S&P 500", "value": 5000.0, "change_percent": 0.0},
            {"ticker": "^DJI", "name": "Dow Jones", "value": 39000.0, "change_percent": 0.0},
            {"ticker": "^IXIC", "name": "Nasdaq", "value": 16000.0, "change_percent": 0.0},
            {"ticker": "^RUT", "name": "Russell 2000", "value": 2000.0, "change_percent": 0.0},
            {"ticker": "^FTSE", "name": "FTSE 100", "value": 8000.0, "change_percent": 0.0},
            {"ticker": "^GDAXI", "name": "DAX Index", "value": 18000.0, "change_percent": 0.0},
            {"ticker": "^FCHI", "name": "CAC 40", "value": 8000.0, "change_percent": 0.0},
            {"ticker": "^N225", "name": "Nikkei 225", "value": 38000.0, "change_percent": 0.0}
        ]
        try:
            loop = asyncio.get_event_loop()
            def fetch():
                import yfinance as yf
                tickers_str = " ".join([d["ticker"] for d in default_indices])
                idxs = yf.Tickers(tickers_str)
                results = []
                for d in default_indices:
                    t = d["ticker"]
                    try:
                        ticker_obj = idxs.tickers[t]
                        info = ticker_obj.info or {}
                        price = info.get("regularMarketPrice") or info.get("currentPrice") or d["value"]
                        change = info.get("regularMarketChangePercent") or 0.0
                        results.append({
                            "ticker": t,
                            "name": d["name"],
                            "value": float(price),
                            "change_percent": float(change)
                        })
                    except Exception as ex:
                        logger.warning(f"Failed to parse yfinance info for index {t}: {ex}")
                        results.append(d)
                return results

            res = await asyncio.wait_for(loop.run_in_executor(None, fetch), timeout=5.0)
            if res:
                return res
        except Exception as e:
            logger.error(f"Error fetching indices dynamically: {e}")
        return default_indices

    @cache_response(ttl=300, prefix="market:movers")
    async def get_movers(self) -> Dict:
        """Fetch stock movers dynamically from yfinance with static fallback."""
        default_movers = {
            "gainers": [
                {"ticker": "NVDA", "price": 950.0, "change_percent": 4.5},
                {"ticker": "TSLA", "price": 180.0, "change_percent": 3.2},
                {"ticker": "AMD", "price": 175.0, "change_percent": 2.8},
                {"ticker": "SMCI", "price": 850.0, "change_percent": 6.1},
                {"ticker": "ARM", "price": 120.0, "change_percent": 4.8},
                {"ticker": "AAPL", "price": 170.0, "change_percent": 1.2}
            ],
            "losers": [
                {"ticker": "COIN", "price": 240.0, "change_percent": -5.2},
                {"ticker": "BABA", "price": 72.0, "change_percent": -3.4},
                {"ticker": "NFLX", "price": 610.0, "change_percent": -2.1},
                {"ticker": "GOOGL", "price": 150.0, "change_percent": -1.8},
                {"ticker": "META", "price": 490.0, "change_percent": -1.5},
                {"ticker": "MSFT", "price": 415.0, "change_percent": -0.8}
            ],
            "active": [
                {"ticker": "TSLA", "price": 180.0, "change_percent": 3.2},
                {"ticker": "NVDA", "price": 950.0, "change_percent": 4.5},
                {"ticker": "AAPL", "price": 170.0, "change_percent": 1.2},
                {"ticker": "AMD", "price": 175.0, "change_percent": 2.8},
                {"ticker": "AMZN", "price": 180.0, "change_percent": -0.5},
                {"ticker": "MSFT", "price": 415.0, "change_percent": -0.8}
            ]
        }
        try:
            loop = asyncio.get_event_loop()
            def fetch():
                import yfinance as yf
                pool = ["AAPL", "MSFT", "NVDA", "TSLA", "AMD", "AMZN", "GOOGL", "META", "NFLX", "AVGO", "SMCI", "ARM", "INTC", "COIN", "BABA"]
                
                try:
                    df = yf.download(pool, period="5d", progress=False)
                    if df is None or df.empty:
                        return None
                    
                    stocks = []
                    for s in pool:
                        try:
                            if 'Close' in df and s in df['Close']:
                                close_series = df['Close'][s].dropna()
                                volume_series = df['Volume'][s].dropna() if 'Volume' in df and s in df['Volume'] else []
                                
                                if len(close_series) >= 2:
                                    current_price = float(close_series.iloc[-1])
                                    prev_price = float(close_series.iloc[-2])
                                    change_pct = float(((current_price - prev_price) / prev_price) * 100)
                                    volume = int(volume_series.iloc[-1]) if len(volume_series) > 0 else 0
                                    
                                    stocks.append({
                                        "ticker": s,
                                        "price": current_price,
                                        "change_percent": change_pct,
                                        "volume": volume
                                    })
                        except Exception as inner_ex:
                            logger.warning(f"Failed parsing downloaded batch data for {s}: {inner_ex}")
                    
                    if not stocks:
                        return None
                        
                    gainers = sorted([s for s in stocks if s["change_percent"] > 0], key=lambda x: x["change_percent"], reverse=True)
                    losers = sorted([s for s in stocks if s["change_percent"] < 0], key=lambda x: x["change_percent"])
                    active = sorted(stocks, key=lambda x: x["volume"], reverse=True)
                    
                    return {
                        "gainers": gainers[:6],
                        "losers": losers[:6],
                        "active": active[:6]
                    }
                except Exception as batch_ex:
                    logger.warning(f"Failed batch yfinance download for movers: {batch_ex}")
                    return None

            res = await asyncio.wait_for(loop.run_in_executor(None, fetch), timeout=12.0)
            if res:
                return res
        except Exception as e:
            logger.error(f"Error fetching movers dynamically: {e}")
        return default_movers

    async def run_screener(self) -> List:
        return []

market_data_service = MarketDataService()

# Export functions for routers to use
async def get_indices():
    return await market_data_service.get_indices()

async def get_movers():
    return await market_data_service.get_movers()

async def run_screener():
    return await market_data_service.run_screener()
