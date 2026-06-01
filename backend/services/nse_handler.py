import requests
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from core.logger import logger
from infrastructure.time_sync import offset_calibrated_datetime

class NSEHandler:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Referer": "https://www.nseindia.com/",
        }
        self.session.headers.update(self.headers)
        self._init_session()

    def _init_session(self):
        """Initializes the NSE session by visiting the home page to get cookies."""
        try:
            logger.info("Initializing NSE session cookies...")
            self.session.get("https://www.nseindia.com/", timeout=10)
            logger.info("NSE session initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize NSE session: {e}")

    def _refresh_session(self):
        """Refreshes cookies if they expire."""
        logger.info("Refreshing NSE session cookies...")
        self._init_session()

    def fetch_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Fetches a stock quote from the unofficial NSE JSON endpoint.
        Expected symbol format: 'RELIANCE' (without .NS)
        """
        ticker = symbol.replace(".NS", "").strip().upper()
        url = f"https://www.nseindia.com/api/quote-equity?symbol={ticker}"

        try:
            response = self.session.get(url, timeout=10)

            # If we hit 401/403/Unexpected, try refreshing session
            if response.status_code in [401, 403]:
                self._refresh_session()
                response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                # The NSE API returns a complex object. We extract the essential bits.
                price_info = data.get("priceInfo", {})
                return {
                    "ticker": symbol,
                    "price": float(price_info.get("lastPrice") or 0.0),
                    "previous_close": float(price_info.get("previousClose") or 0.0),
                    "change": float(price_info.get("change") or 0.0),
                    "change_percent": float(price_info.get("pChange") or 0.0),
                    "open": float(price_info.get("open") or 0.0),
                    "high": float(price_info.get("high") or 0.0),
                    "low": float(price_info.get("low") or 0.0),
                    "volume": data.get("volume", {}).get("totalTradedVolume") or 0,
                    "source": "NSE Unofficial",
                    "timestamp": offset_calibrated_datetime().timestamp()
                }

            logger.warning(f"NSE API returned HTTP {response.status_code} for {ticker}")
            return None
        except Exception as e:
            logger.error(f"Error fetching quote from NSE for {ticker}: {e}")
            return None

# Singleton instance
nse_handler = NSEHandler()
