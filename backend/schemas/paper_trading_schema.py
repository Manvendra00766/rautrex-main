from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, List, Any
import re

class PlaceOrderRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Z0-9.\=]+$")
    side: Literal["BUY", "SELL"]
    quantity: int = Field(..., gt=0)
    order_type: Literal["MARKET", "LIMIT"] = "MARKET"
    limit_price: Optional[float] = Field(None, gt=0)

    @field_validator("ticker", mode="before")
    @classmethod
    def sanitize_ticker(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("Ticker must be a string")
        # Trim leading and trailing spaces
        cleaned = v.strip()
        # Strip script blocks completely including their content (e.g. <script>alert(1)</script>)
        cleaned = re.sub(r"<script.*?>.*?</script>", "", cleaned, flags=re.IGNORECASE)
        # Strip all other HTML tags
        cleaned = re.sub(r"<[^>]*>", "", cleaned)
        # Strip any stray 'script' words to prevent bypass
        cleaned = re.sub(r"script", "", cleaned, flags=re.IGNORECASE)
        # Convert to uppercase
        return cleaned.upper()

class Order(BaseModel):
    id: str
    user_id: str
    ticker: str
    side: str
    quantity: int
    order_type: str
    limit_price: Optional[float] = None
    executed_price: Optional[float] = None
    status: Literal["EXECUTED", "REJECTED"]
    created_at: str

class Position(BaseModel):
    ticker: str
    quantity: int
    avg_buy_price: float
    current_price: float
    pnl: float
    pnl_pct: float
    total_value: float

class Portfolio(BaseModel):
    cash_balance: float
    total_invested: float
    total_current_value: float
    total_pnl: float
    total_pnl_pct: float
    positions: List[Position]
