import re
import urllib.parse
from typing import Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.logger import logger
from models.user_data import CompanyTickerMapping

class TickerResolverService:
    def __init__(self):
        # Enforce standard desktop browser User-Agent to prevent rate-limiting/blocking by Yahoo
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
        }
        self.timeout = 8.0

    def normalize_query(self, query: str) -> str:
        """Clean and normalize user query to prevent duplicate semantic mappings in SQLite."""
        if not query:
            return ""
        # Convert to lower case, strip whitespace, replace multiple spaces/tabs/newlines with a single space
        cleaned = query.strip().lower()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    async def resolve(self, query: str, db: AsyncSession) -> Optional[str]:
        """
        Resolves a friendly name into a standard ticker with a two-tier lookup:
        Tier 1: SQLite local mapping cache (Instant, < 0.5ms)
        Tier 2: Yahoo Search API resolution & auto-caching
        """
        normalized = self.normalize_query(query)
        if not normalized:
            return None

        # ----------------------------------------------------
        # TIER 1: SQLite local cache check
        # ----------------------------------------------------
        try:
            stmt = select(CompanyTickerMapping).where(CompanyTickerMapping.user_query == normalized)
            result = await db.execute(stmt)
            mapping = result.scalar_one_or_none()
            if mapping:
                logger.debug(f"[TickerResolver] Cache HIT for query '{normalized}' -> '{mapping.resolved_ticker}'")
                return mapping.resolved_ticker
        except Exception as cache_err:
            logger.warning(f"[TickerResolver] Local database cache query failed: {cache_err}")

        # ----------------------------------------------------
        # TIER 2: Live Yahoo Search API query
        # ----------------------------------------------------
        logger.info(f"[TickerResolver] Cache MISS for query '{normalized}'. Fetching from Yahoo Finance...")
        encoded_query = urllib.parse.quote(normalized)
        search_url = f"https://query1.finance.yahoo.com/v1/finance/search?q={encoded_query}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(search_url, headers=self.headers, timeout=self.timeout)
                
                if response.status_code != 200:
                    logger.warning(f"[TickerResolver] Yahoo API returned status {response.status_code}: {response.text}")
                    return None
                
                payload = response.json()
                quotes = payload.get("quotes", [])
                
                if not quotes:
                    logger.info(f"[TickerResolver] No search matches found on Yahoo Finance for '{normalized}'")
                    return None
                
                # Retrieve top-ranked quote symbol
                resolved_ticker = quotes[0].get("symbol")
                if not resolved_ticker:
                    return None
                
                resolved_ticker = resolved_ticker.strip().upper()
                
                # ----------------------------------------------------
                # Auto-Learn: Cache resolved mapping in local DB
                # ----------------------------------------------------
                try:
                    new_mapping = CompanyTickerMapping(
                        user_query=normalized,
                        resolved_ticker=resolved_ticker,
                        confidence_score=1.0
                    )
                    db.add(new_mapping)
                    await db.commit()
                    logger.info(f"[TickerResolver] Learned & cached mapping: '{normalized}' -> '{resolved_ticker}'")
                except Exception as save_err:
                    # Roll back changes in session if mapping commit generates an exception (e.g. duplicate key race condition)
                    await db.rollback()
                    logger.warning(f"[TickerResolver] Failed saving mapping cache: {save_err}")
                
                return resolved_ticker
                
        except httpx.RequestError as net_err:
            logger.error(f"[TickerResolver] Network request failed for query '{normalized}': {net_err}")
        except Exception as err:
            logger.error(f"[TickerResolver] Unhandled exception resolving query '{normalized}': {err}")
            
        return None

ticker_resolver_service = TickerResolverService()
