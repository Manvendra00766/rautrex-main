import asyncio
from typing import Set
from core.logger import logger
from services.market_data_service import market_data_service
from websocket_app.manager import manager
from repositories.portfolio_repo import portfolio_position_repo

class MarketStreamingEngine:
    def __init__(self):
        self.active_tickers: Set[str] = set()
        self.is_running = False
        self._task: asyncio.Task | None = None
        self._price_cache = {}

    def add_ticker(self, ticker: str):
        self.active_tickers.add(ticker)

    def remove_ticker(self, ticker: str):
        self.active_tickers.discard(ticker)
        self._price_cache.pop(ticker, None)

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

    async def _stream_loop(self):
        """Continuously fetches prices for active tickers and broadcasts them on change."""
        while self.is_running:
            try:
                if not self.active_tickers:
                    await asyncio.sleep(5)
                    continue

                tickers_to_fetch = list(self.active_tickers)
                logger.debug(f"Streaming data for {len(tickers_to_fetch)} tickers...")
                
                # Use batch fetching from market data service
                market_data = await market_data_service.fetch_batch(tickers_to_fetch)
                
                # Broadcast and update DB in the background
                broadcast_tasks = []
                db_tasks = []
                
                for ticker, data in market_data.items():
                    if data:
                        # Extract price (assuming a standard schema from market_data_service)
                        price = data.get("price") or data.get("c") or data.get("regularMarketPrice")
                        if price is not None:
                            # Caching Check: Only send updates if price changed or was not cached
                            cached_price = self._price_cache.get(ticker)
                            if cached_price == price:
                                logger.debug(f"Streaming: Ticker {ticker} price {price} unchanged. Skipping DB update and WS broadcast.")
                                continue
                                
                            # Update local price cache
                            self._price_cache[ticker] = price
                            
                            message = {
                                "type": "market_update",
                                "ticker": ticker,
                                "price": price,
                                "timestamp": data.get("timestamp")
                            }
                            # Broadcast to clients subscribed to 'market' or specific ticker channels
                            broadcast_tasks.append(manager.broadcast_to_channel("market", message))
                            broadcast_tasks.append(manager.broadcast_to_channel(f"ticker:{ticker}", message))
                            
                            # Async update positions in the DB without blocking the stream
                            db_tasks.append(portfolio_position_repo.update_current_price(ticker, price))

                if broadcast_tasks:
                    await asyncio.gather(*broadcast_tasks, return_exceptions=True)
                if db_tasks:
                    asyncio.create_task(asyncio.gather(*db_tasks, return_exceptions=True))

            except Exception as e:
                logger.error(f"Streaming loop error: {e}")

            # Sleep to prevent rate limit exhaustion (e.g., 5 seconds)
            await asyncio.sleep(5)

streaming_engine = MarketStreamingEngine()
