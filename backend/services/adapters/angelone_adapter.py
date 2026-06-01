import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
import httpx
import pyotp

from core.logger import logger
from core.config import settings
from infrastructure.redis_client import redis_client
from services.pricing_engine import (
    PriceSnapshot, infer_asset_type, SECTOR_MAP
)
from .base_adapter import BaseMarketAdapter
from infrastructure.time_sync import offset_calibrated_datetime

class AngelOneAdapter(BaseMarketAdapter):
    def __init__(self, executor=None):
        self.executor = executor
        self.client = httpx.AsyncClient(timeout=10.0)
        self.api_key = settings.ANGELONE_API_KEY
        self.client_id = settings.ANGELONE_CLIENT_ID
        self.password = settings.ANGELONE_PASSWORD
        self.totp_token = settings.ANGELONE_TOTP_TOKEN

    async def get_token(self) -> Optional[str]:
        """Retrieve the active JWT from Redis or return None."""
        token = await redis_client.get("angelone:jwt")
        return token

    async def refresh_token(self) -> Optional[str]:
        """Perform automated token refresh using TOTP."""
        try:
            totp = pyotp.TOTP(self.totp_token)
            current_totp = totp.now()

            # Angel One SmartAPI Session Generation
            url = "https://smartapi.angelone.in/auth/smartapi-auth/login"
            payload = {
                "api_key": self.api_key,
                "client_id": self.client_id,
                "password": self.password,
                "totp": current_totp
            }

            response = await self.client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                jwt_token = data.get("data", {}).get("jwtToken")
                refresh_token = data.get("data", {}).get("refreshToken")

                if jwt_token:
                    # Store in Redis with 24hr TTL
                    await redis_client.set("angelone:jwt", jwt_token, ex=86400)
                    await redis_client.set("angelone:refresh_token", refresh_token, ex=86400 * 7)
                    logger.info("Angel One token refreshed successfully.")
                    return jwt_token

            logger.error(f"Angel One token refresh failed (HTTP {response.status_code}): {response.text}")
            return None
        except Exception as e:
            logger.error(f"Exception during Angel One token refresh: {e}")
            return None

    async def fetch_price(self, symbol: str) -> Optional[PriceSnapshot]:
        symbol_upper = symbol.strip().upper()
        token = await self.get_token()

        if not token:
            logger.warning(f"[AngelOneAdapter] No active token for {symbol_upper}. Fetch unavailable.")
            return None

        try:
            # Angel One uses instrument tokens. We need to resolve the symbol to a token.
            # For simplicity in this adapter, we assume a resolver service provides it.
            from services.ticker_resolver import ticker_resolver_service
            token_id = await ticker_resolver_service.get_angelone_token(symbol_upper)
            if not token_id:
                return None

            url = "https://smartapi.angelone.in/market/LTP"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            payload = {
                "exchange": "NSE", # Default to NSE for Indian equities
                "symbol": symbol_upper,
                "token": token_id
            }

            response = await self.client.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json().get("data", {})
                if not data:
                    return None

                ltp = float(data.get("last_traded_price") or 0.0)

                return PriceSnapshot(
                    symbol=symbol_upper,
                    name=symbol_upper,
                    asset_type="equity",
                    currency="INR",
                    exchange="NSE",
                    sector=SECTOR_MAP.get(symbol_upper, "Indian Equity"),
                    country="IN",
                    market_cap=None,
                    previous_close=ltp, # Simplified
                    last_price=ltp,
                    change_amount=0.0, # Need full quote for this
                    change_percent=0.0,
                    volume=None,
                    source="AngelOne",
                    fetched_at=offset_calibrated_datetime(),
                    raw=data
                )
            return None
        except Exception as e:
            logger.error(f"[AngelOneAdapter] Error fetching Angel One price for {symbol_upper}: {e}")
            return None

    async def fetch_history(self, symbol: str, period: str = "1mo") -> List[Dict[str, Any]]:
        # Implementation of history fetch using Angel One Candle API
        # For brevity and as per the primary requirement, focuses on the Quote fetcher first.
        return []

    async def fetch_batch(self, symbols: List[str]) -> Dict[str, Optional[PriceSnapshot]]:
        tasks = [self.fetch_price(s) for s in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for s, res in zip(symbols, results):
            if isinstance(res, Exception) or res is None:
                output[s] = None
            else:
                output[s] = res
        return output
