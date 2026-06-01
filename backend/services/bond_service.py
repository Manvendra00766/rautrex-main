import requests
from bs4 import BeautifulSoup
from typing import Dict, Any, List, Optional
from core.logger import logger
from infrastructure.redis_client import redis_client
from infrastructure.time_sync import offset_calibrated_datetime

class BondService:
    def __init__(self):
        self.fbil_url = "https://www.fbil.org.in/benchmark-rates.html"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/\*;q=0.8",
        }

    async def fetch_gsec_yields(self) -> Dict[str, Any]:
        """
        Scrapes benchmark G-Sec yields from FBIL.
        Returns a map of tenor to yield.
        """
        try:
            logger.info("Fetching G-Sec yields from FBIL...")
            response = requests.get(self.fbil_url, headers=self.headers, timeout=15)
            if response.status_code != 200:
                logger.error(f"FBIL fetch failed with status {response.status_code}")
                return await self._get_cached_yields()

            soup = BeautifulSoup(response.text, "html.parser")
            yields = {}

            # FBIL benchmark rates are typically in tables.
            # We look for rows containing G-Sec tenors like '10 Year'
            tables = soup.find_all("table")
            for table in tables:
                rows = table.find_all("tr")
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        tenor = cols[0].text.strip()
                        value = cols[1].text.strip()

                        if "10 Year" in tenor:
                            yields["10Y"] = self._clean_yield(value)
                        elif "5 Year" in tenor:
                            yields["5Y"] = self._clean_yield(value)
                        elif "2 Year" in tenor:
                            yields["2Y"] = self._clean_yield(value)
                        elif "91 Day" in tenor:
                            yields["91D"] = self._clean_yield(value)

            if not yields:
                logger.warning("FBIL scrape found no matching G-Sec tenors.")
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

        # Ultimate fallback
        return {
            "yields": {"10Y": 7.0, "5Y": 6.8, "2Y": 6.5, "91D": 6.4},
            "timestamp": offset_calibrated_datetime().isoformat(),
            "source": "Fallback",
            "stale": True
        }

bond_service = BondService()
