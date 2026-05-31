import asyncio
from typing import Set, Dict, Any
from datetime import datetime, timezone
from core.logger import logger
from websocket_app.manager import manager
from repositories.portfolio_repo import portfolio_position_repo

UTC = timezone.utc


class MarketStreamingEngine:
    def __init__(self):
        self.active_tickers: Set[str] = set()
        self.is_running = False
        self._task: asyncio.Task | None = None
        self._price_cache: Dict[str, float] = {}

    def add_ticker(self, ticker: str):
        """Register a ticker for live price tracking."""
        cleaned = ticker.strip().upper()
        if cleaned and cleaned not in self.active_tickers:
            self.active_tickers.add(cleaned)
            logger.info(f"Streaming: Added ticker {cleaned}. Total tracked: {len(self.active_tickers)}")

    def add_tickers(self, tickers):
        """Register multiple tickers for live price tracking."""
        for ticker in tickers:
            self.add_ticker(ticker)

    def remove_ticker(self, ticker: str):
        cleaned = ticker.strip().upper()
        self.active_tickers.discard(cleaned)
        self._price_cache.pop(cleaned, None)

    async def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._task = asyncio.create_task(self._stream_loop())
        logger.info("Market Streaming Engine started.")

    async def stop(self):
        self.is_running = False
        if self._task:
            self._task.cancel()
        logger.info("Market Streaming Engine stopped.")

    async def load_tickers_from_portfolios(self):
        """Auto-discover tickers from all portfolio positions in the database."""
        try:
            from supabase_client import supabase
            response = supabase.table("portfolio_positions").select("ticker").execute()
            rows = response.data or []
            tickers = set()
            for row in rows:
                t = row.get("ticker")
                if t:
                    tickers.add(t.strip().upper())
            if tickers:
                self.add_tickers(tickers)
                logger.info(f"Streaming: Auto-loaded {len(tickers)} tickers from portfolio positions.")
        except Exception as e:
            logger.error(f"Streaming: Failed to auto-load tickers from portfolios: {e}")

    async def _fetch_prices_yfinance(self, tickers: list) -> Dict[str, Dict[str, Any]]:
        """Fetch current prices for a batch of tickers using yfinance and pricing_engine fallbacks."""
        # Separate G-Sec/Government debt tickers from standard tickers
        gsec_tickers = []
        standard_tickers = []
        for t in tickers:
            t_upper = t.upper()
            if "GS" in t_upper or "GB" in t_upper or "709GS" in t_upper:
                gsec_tickers.append(t)
            else:
                standard_tickers.append(t)

        results = {}

        # 1. Fetch standard tickers from yfinance
        if standard_tickers:
            loop = asyncio.get_event_loop()
            def _fetch():
                import yfinance as yf
                sub_results = {}
                try:
                    tickers_str = " ".join(standard_tickers)
                    data = yf.Tickers(tickers_str)
                    for t in standard_tickers:
                        try:
                            ticker_obj = data.tickers.get(t)
                            if not ticker_obj:
                                continue
                            info = ticker_obj.info or {}
                            price = info.get("regularMarketPrice") or info.get("currentPrice")
                            prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
                            if price is not None:
                                change_amount = (price - prev_close) if prev_close else 0.0
                                change_percent = ((change_amount / prev_close) * 100) if prev_close and prev_close != 0 else 0.0
                                sub_results[t] = {
                                    "price": float(price),
                                    "previous_close": float(prev_close) if prev_close else None,
                                    "change_amount": float(change_amount),
                                    "change_percent": float(change_percent),
                                    "volume": info.get("regularMarketVolume"),
                                    "name": info.get("longName") or info.get("shortName") or t,
                                    "currency": info.get("currency") or "USD",
                                    "exchange": info.get("exchange"),
                                    "sector": info.get("sector"),
                                    "country": info.get("country"),
                                    "market_cap": info.get("marketCap"),
                                    "timestamp": datetime.now(tz=UTC).isoformat()
                                }
                        except Exception as ex:
                            logger.warning(f"Streaming: yfinance fetch failed for {t}: {ex}")
                except Exception as e:
                    logger.error(f"Streaming: yfinance batch fetch failed: {e}")
                return sub_results

            yfinance_results = await loop.run_in_executor(None, _fetch)
            results.update(yfinance_results)

        # 2. Fetch G-Sec tickers from pricing_engine
        if gsec_tickers:
            try:
                from services.pricing_engine import get_batch_price_snapshots
                snapshots = await get_batch_price_snapshots(gsec_tickers, max_age_seconds=10)
                for t in gsec_tickers:
                    snap = snapshots.get(t)
                    if snap:
                        results[t] = {
                            "price": snap.last_price,
                            "previous_close": snap.previous_close,
                            "change_amount": snap.change_amount,
                            "change_percent": snap.change_percent,
                            "volume": snap.volume,
                            "name": snap.name or t,
                            "currency": snap.currency or "INR",
                            "exchange": snap.exchange or "NSE_GS",
                            "sector": "Government Securities",
                            "country": snap.country or "IN",
                            "market_cap": snap.market_cap,
                            "timestamp": snap.fetched_at.isoformat() if hasattr(snap.fetched_at, "isoformat") else datetime.now(tz=UTC).isoformat()
                        }
            except Exception as e:
                logger.error(f"Streaming: pricing_engine G-Sec fetch failed: {e}")

        return results

    async def _upsert_market_cache(self, ticker: str, data: Dict[str, Any]):
        """Write the latest price to Supabase market_cache table to trigger Realtime updates."""
        try:
            from supabase_client import supabase

            record = {
                "symbol": ticker,
                "name": data.get("name") or ticker,
                "asset_type": "equity",
                "currency": data.get("currency") or "USD",
                "exchange": data.get("exchange"),
                "sector": data.get("sector"),
                "country": data.get("country"),
                "market_cap": data.get("market_cap"),
                "previous_close": data.get("previous_close"),
                "last_price": data["price"],
                "change_amount": data.get("change_amount", 0.0),
                "change_percent": data.get("change_percent", 0.0),
                "volume": data.get("volume"),
                "source": "streaming_engine",
                "fetched_at": data.get("timestamp") or datetime.now(tz=UTC).isoformat(),
                "raw": {}
            }

            await asyncio.to_thread(
                lambda: supabase.table("market_cache").upsert(record).execute()
            )
        except Exception as e:
            logger.warning(f"Streaming: Failed to upsert market_cache for {ticker}: {e}")

    async def _stream_loop(self):
        """Continuously fetches prices for active tickers and broadcasts them on change."""
        # On first run, auto-load tickers from portfolio positions
        await self.load_tickers_from_portfolios()

        while self.is_running:
            try:
                if not self.active_tickers:
                    await asyncio.sleep(5)
                    continue

                tickers_to_fetch = list(self.active_tickers)
                logger.debug(f"Streaming data for {len(tickers_to_fetch)} tickers...")

                # Fetch prices using yfinance (reliable, no API key needed)
                market_data = await self._fetch_prices_yfinance(tickers_to_fetch)

                broadcast_tasks = []
                db_tasks = []
                cache_tasks = []

                for ticker, data in market_data.items():
                    price = data.get("price")
                    if price is None:
                        continue

                    # Only send updates if price actually changed
                    cached_price = self._price_cache.get(ticker)
                    if cached_price == price:
                        logger.debug(f"Streaming: {ticker} price {price} unchanged. Skipping.")
                        continue

                    # Update local price cache
                    self._price_cache[ticker] = price

                    # 1. Broadcast via WebSocket to connected clients
                    message = {
                        "type": "market_update",
                        "ticker": ticker,
                        "price": price,
                        "change_amount": data.get("change_amount", 0.0),
                        "change_percent": data.get("change_percent", 0.0),
                        "timestamp": data.get("timestamp")
                    }
                    broadcast_tasks.append(manager.broadcast_to_channel("market", message))
                    broadcast_tasks.append(manager.broadcast_to_channel(f"ticker:{ticker}", message))

                    # 2. Update portfolio positions current_price in DB
                    db_tasks.append(portfolio_position_repo.update_current_price(ticker, price))

                    # 3. Upsert to Supabase market_cache (triggers Realtime for frontend)
                    cache_tasks.append(self._upsert_market_cache(ticker, data))

                async def run_gathered(tasks):
                    await asyncio.gather(*tasks, return_exceptions=True)

                if broadcast_tasks:
                    await asyncio.gather(*broadcast_tasks, return_exceptions=True)
                if db_tasks:
                    asyncio.create_task(run_gathered(db_tasks))
                if cache_tasks:
                    asyncio.create_task(run_gathered(cache_tasks))

                logger.debug(f"Streaming: Updated {len(market_data)} tickers.")

            except Exception as e:
                logger.error(f"Streaming loop error: {e}")

            # Poll interval: 30 seconds to stay within yfinance rate limits
            # yfinance is not truly real-time, so polling faster wastes resources
            await asyncio.sleep(30)

streaming_engine = MarketStreamingEngine()
