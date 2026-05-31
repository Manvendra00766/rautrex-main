from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.logger import logger
from models.user_data import Instrument
from services.market_data_service import market_data_service

class TickerMasterService:
    """
    TickerMasterService implements the "Lazy Synchronization & Active Tracking" pattern.
    Rather than syncing thousands of unused tickers, it stores and maintains ONLY
    active tradeable instruments in local SQLite to optimize speed, space (<5MB), and bandwidth.
    """

    async def lazy_sync_ticker(self, symbol: str, db: AsyncSession) -> Optional[Instrument]:
        """
        Retrieves a ticker from SQLite, or lazy-syncs it from gateway APIs if missing.
        """
        symbol_upper = symbol.strip().upper()
        if not symbol_upper:
            return None

        # 1. Check local SQLite cache first
        try:
            stmt = select(Instrument).where(Instrument.symbol == symbol_upper)
            result = await db.execute(stmt)
            instrument = result.scalar_one_or_none()
            if instrument:
                logger.debug(f"[TickerMaster] Cache HIT for instrument symbol: '{symbol_upper}'")
                return instrument
        except Exception as e:
            logger.warning(f"[TickerMaster] Local database fetch failed for {symbol_upper}: {e}")

        # 2. Cache MISS: Fetch latest metadata via Gateways/Adapters
        logger.info(f"[TickerMaster] Cache MISS for instrument '{symbol_upper}'. Lazy syncing from gateway...")
        try:
            snapshot = await market_data_service.fetch_price(symbol_upper)
            if not snapshot or snapshot.get("price") == 0.0:
                logger.warning(f"[TickerMaster] Could not resolve market metadata for '{symbol_upper}'. Skipping cache.")
                return None

            # Map unified snapshot schema to local SQLAlchemy Instrument
            new_instrument = Instrument(
                symbol=symbol_upper,
                name=snapshot.get("name") or symbol_upper,
                exchange=snapshot.get("exchange") or "UNKNOWN",
                currency=snapshot.get("currency") or "USD",
                sector=snapshot.get("sector") or "Unknown",
                asset_type=snapshot.get("asset_type") or "equity",
                is_tracked=True,
                last_synced_at=datetime.now(timezone.utc)
            )

            db.add(new_instrument)
            await db.commit()
            logger.info(f"[TickerMaster] Successfully synced and cached '{symbol_upper}' in SQLite.")
            return new_instrument

        except Exception as err:
            await db.rollback()
            logger.error(f"[TickerMaster] Unhandled exception lazy syncing '{symbol_upper}': {err}")
            return None

    async def get_tracked_instruments(self, db: AsyncSession) -> List[Instrument]:
        """
        Retrieves all actively tracked instruments in SQLite.
        """
        try:
            stmt = select(Instrument).where(Instrument.is_tracked == True)
            result = await db.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"[TickerMaster] Failed to fetch active instruments: {e}")
            return []

    async def sync_active_instruments(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Core Daily Cron Job (4:00 AM): Refreshes local metadata of actively tracked assets.
        Operates with error isolation so one failed asset does not block the sync sequence.
        """
        logger.info("[TickerMaster] Starting daily active instruments metadata sync...")
        tracked = await self.get_tracked_instruments(db)
        if not tracked:
            logger.info("[TickerMaster] No tracked instruments to synchronize.")
            return {"synced_count": 0, "failures": 0}

        synced_count = 0
        failures = 0

        # Concurrently fetch metadata for all active instruments using the gateways
        symbols = [inst.symbol for inst in tracked]
        try:
            # Leverage batch fetching to prevent rate limiting
            price_map = await market_data_service.fetch_batch(symbols)
        except Exception as batch_err:
            logger.error(f"[TickerMaster] Batch price fetch failed during daily cron: {batch_err}")
            price_map = {}

        for inst in tracked:
            symbol = inst.symbol
            snapshot = price_map.get(symbol)
            
            # If batch fetch failed, perform a resilient single fallback
            if not snapshot or snapshot.get("price") == 0.0:
                try:
                    snapshot = await market_data_service.fetch_price(symbol)
                except Exception:
                    snapshot = None

            if snapshot and snapshot.get("price") != 0.0:
                try:
                    inst.name = snapshot.get("name") or inst.name
                    inst.exchange = snapshot.get("exchange") or inst.exchange
                    inst.currency = snapshot.get("currency") or inst.currency
                    inst.sector = snapshot.get("sector") or inst.sector
                    inst.asset_type = snapshot.get("asset_type") or inst.asset_type
                    inst.last_synced_at = datetime.now(timezone.utc)
                    synced_count += 1
                except Exception as update_err:
                    logger.warning(f"[TickerMaster] Failed updating SQLite record for {symbol}: {update_err}")
                    failures += 1
            else:
                logger.warning(f"[TickerMaster] Skipping sync for {symbol}: gateway unreachable. Retaining local data.")
                failures += 1

        try:
            await db.commit()
            logger.info(f"[TickerMaster] Daily sync complete. Synced: {synced_count}, Failures: {failures}")
        except Exception as commit_err:
            await db.rollback()
            logger.error(f"[TickerMaster] Failed to commit daily sync changes: {commit_err}")
            return {"synced_count": 0, "failures": len(tracked)}

        return {"synced_count": synced_count, "failures": failures}

ticker_master_service = TickerMasterService()
