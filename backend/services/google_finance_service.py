import httpx
import re
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from core.logger import logger

class GoogleFinanceService:
    def __init__(self):
        self.base_url = "https://www.google.com/finance/quote/"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def fetch_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Scrapes price data from Google Finance using highly targeted 2025 DOM selectors.
        Supports Indian stocks (e.g., RELIANCE:NSE).
        """
        # Convert .NS / .BO to :NSE / :BSE
        clean_symbol = symbol.strip().upper()
        if clean_symbol.endswith(".NS"):
            ticker = clean_symbol[:-3] + ":NSE"
        elif clean_symbol.endswith(".BO"):
            ticker = clean_symbol[:-3] + ":BSE"
        else:
            # If no exchange provided, assume NSE for Indian-looking tickers
            if ":" not in clean_symbol:
                ticker = f"{clean_symbol}:NSE"
            else:
                ticker = clean_symbol

        url = f"{self.base_url}{ticker}"
        
        try:
            async with httpx.AsyncClient(headers=self.headers, follow_redirects=True) as client:
                response = await client.get(url, timeout=10.0)
                
            if response.status_code != 200:
                logger.warning(f"Google Finance returned {response.status_code} for {ticker}")
                return None

            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            
            # 1. Extract Last Price
            # Container class .N6SYTe is the primary price wrapper in 2025
            price_el = soup.select_one(".N6SYTe")
            if not price_el:
                # Fallback to jsname="Pdsbrc" or older classes
                price_el = soup.select_one('span[jsname="Pdsbrc"], div[data-last-price], .YMlKec.fx170e')
            
            if not price_el:
                logger.warning(f"Could not find price element on Google Finance for {ticker}")
                return None

            # Clean price string (e.g., "₹1,320.20" -> 1320.20)
            price_text = price_el.text.strip()
            # Remove all non-numeric characters except the decimal point
            price_cleaned = re.sub(r'[^\d.]', '', price_text)
            
            try:
                price = float(price_cleaned)
            except ValueError:
                logger.warning(f"Could not parse price '{price_text}' for {ticker}")
                return None

            # 2. Extract Change and Percentage
            # These are typically in a sibling div with class .DAicsd
            change_percent = 0.0
            change_amount = 0.0

            change_container = soup.select_one(".DAicsd")
            if change_container:
                text = change_container.text.strip()
                # Text looks like "arrow_downward-0.08%(-1.00) 1D"
                # Extract percentage (e.g., -0.08)
                pct_match = re.search(r"([+-]?[\d,]+\.\d+)\%", text)
                if pct_match:
                    change_percent = float(pct_match.group(1).replace(",", ""))
                
                # Extract absolute change (e.g., -1.00)
                # Usually inside parentheses
                amt_match = re.search(r"\(([+-]?[\d,]+\.\d+)\)", text)
                if amt_match:
                    change_amount = float(amt_match.group(1).replace(",", ""))

            # 3. Extract Name
            # The div with class "gO24Ff" contains the long name
            name_el = soup.select_one(".gO24Ff, .zz19u")
            name = name_el.text.strip() if name_el else symbol

            return {
                "symbol": symbol,
                "ticker": ticker,
                "price": price,
                "previous_close": price - change_amount,
                "change_amount": change_amount,
                "change_percent": change_percent,
                "name": name,
                "source": "Google Finance",
                "timestamp": datetime.now(tz=timezone.utc).timestamp()
            }

        except Exception as e:
            logger.error(f"Error scraping Google Finance for {ticker}: {e}")
            return None

# Singleton instance
google_finance_service = GoogleFinanceService()
