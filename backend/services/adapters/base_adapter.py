from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from services.pricing_engine import PriceSnapshot

class BaseMarketAdapter(ABC):
    @abstractmethod
    async def fetch_price(self, symbol: str) -> Optional[PriceSnapshot]:
        """Fetch the latest price snapshot for a single symbol."""
        pass

    @abstractmethod
    async def fetch_history(self, symbol: str, period: str = "1mo") -> List[Dict[str, Any]]:
        """Fetch historical candle/price records for a symbol."""
        pass

    @abstractmethod
    async def fetch_batch(self, symbols: List[str]) -> Dict[str, Optional[PriceSnapshot]]:
        """Fetch latest price snapshots for multiple symbols concurrently."""
        pass
