from typing import List, Optional
from pydantic import BaseModel
from .base import BaseRepository

class PortfolioSchema(BaseModel):
    id: Optional[str] = None
    user_id: str
    name: str
    total_value: float
    currency: str = "USD"
    created_at: Optional[str] = None

class PortfolioRepository(BaseRepository[PortfolioSchema]):
    def __init__(self):
        super().__init__(table_name="portfolios", model_class=PortfolioSchema)

    async def get_by_user_id(self, user_id: str) -> List[PortfolioSchema]:
        return await self.get_all({"user_id": user_id})

class PortfolioPositionSchema(BaseModel):
    id: Optional[str] = None
    portfolio_id: str
    ticker: str
    shares: float
    avg_cost_price: float
    current_price: Optional[float] = None
    last_updated: Optional[str] = None

class PortfolioPositionRepository(BaseRepository[PortfolioPositionSchema]):
    def __init__(self):
        super().__init__(table_name="portfolio_positions", model_class=PortfolioPositionSchema)

    async def get_by_portfolio_id(self, portfolio_id: str) -> List[PortfolioPositionSchema]:
        return await self.get_all({"portfolio_id": portfolio_id})

    async def update_current_price(self, ticker: str, new_price: float):
        # The 'portfolio_positions' table does not have a 'current_price' column in the schema.
        # Prices are dynamically resolved from 'market_cache' at query time.
        pass

portfolio_repo = PortfolioRepository()
portfolio_position_repo = PortfolioPositionRepository()
