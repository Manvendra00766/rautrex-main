import asyncio
import httpx
from typing import Dict
from core.logger import logger

class FXRateService:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(FXRateService, cls).__new__(cls, *args, **kwargs)
        return cls._instance
        
    def __init__(self):
        if not hasattr(self, "initialized"):
            self.rates: Dict[str, float] = {"USD_INR": 83.50, "INR_USD": 1.0 / 83.50}
            self.initialized = True
            
    async def fetch_latest_rates(self):
        """Poll Yahoo Finance once every 5 minutes to get the latest USD/INR exchange rate."""
        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/USDINR=X"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                    price = meta.get("regularMarketPrice")
                    if price:
                        self.rates["USD_INR"] = float(price)
                        self.rates["INR_USD"] = 1.0 / float(price)
                        logger.info(f"[FXRateService] Updated USD/INR rate: {price}")
                else:
                    logger.warning(f"[FXRateService] API returned non-200 status {res.status_code}. Using cached rates: {self.rates}")
        except Exception as e:
            logger.warning(f"[FXRateService] Failed to poll live FX rates: {e}. Using cached rates: {self.rates}")

fx_rate_service = FXRateService()
