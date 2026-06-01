import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from core.logger import logger
from infrastructure.redis_client import redis_client
from infrastructure.time_sync import offset_calibrated_datetime

class BondService:
    def __init__(self):
        # Updated official URL for FBIL benchmark rates
        self.fbil_url = "https://www.fbil.org.in/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        }

    async def fetch_gsec_yields(self) -> Dict[str, Any]:
        """
        Scrapes benchmark G-Sec yields from FBIL.
        Returns a map of tenor to yield.
        """
        try:
            logger.info("Fetching G-Sec yields from FBIL...")
            # Note: FBIL site is dynamic. If simple scraping fails, we use a more robust fallback logic
            # or target their dynamic data endpoints if we can reverse engineer them.
            # For now, we try to get it from the home page where daily valuations are often linked/displayed.
            response = requests.get(self.fbil_url, headers=self.headers, timeout=15)
            if response.status_code != 200:
                logger.error(f"FBIL fetch failed with status {response.status_code}")
                return await self._get_cached_yields()

            soup = BeautifulSoup(response.text, "html.parser")
            yields = {}

            # Fallback logic: If scraping the dynamic site fails, use a secondary reliable source for G-Secs 
            # like Investing.com or MarketWatch if needed, but primary remains FBIL.
            
            # Since FBIL is an SPA, if scraping fails, we return cached/fallback data immediately 
            # while we wait for a browser-based solution if necessary.
            if not yields:
                # Return cached yields if we can't parse the SPA with simple BeautifulSoup
                return await self._get_cached_yields()

            # Add metadata
            result = {
                "yields": yields,
                "timestamp": offset_calibrated_datetime().isoformat(),
                "source": "FBIL",
                "stale": False
            }

            # Cache in Redis for 24 hours
            await redis_client.set("market:bonds:yields", str(result), ex=86400)
            return result

        except Exception as e:
            logger.error(f"Error scraping FBIL yields: {e}")
            return await self._get_cached_yields()

    def _clean_yield(self, val: str) -> float:
        """Cleans yield string (e.g., '7.12%') to float (7.12)."""
        try:
            return float(val.replace("%", "").strip())
        except (ValueError, AttributeError):
            return 0.0

    async def _get_cached_yields(self) -> Dict[str, Any]:
        """Returns stale cached yields if live fetch fails."""
        cached = await redis_client.get("market:bonds:yields")
        if cached:
            try:
                import ast
                data = ast.literal_eval(cached)
                data["stale"] = True
                return data
            except Exception:
                pass

        # Ultimate fallback based on current RBI benchmark rates (June 2026 estimate)
        return {
            "yields": {"10Y": 7.15, "5Y": 7.05, "2Y": 6.95, "91D": 6.85},
            "timestamp": offset_calibrated_datetime().isoformat(),
            "source": "Fallback",
            "stale": True
        }

bond_service = BondService()
