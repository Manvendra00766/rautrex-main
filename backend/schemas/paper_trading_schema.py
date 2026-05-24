from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional, List
from datetime import datetime

class PlaceOrderRequest(BaseModel):
    ticker: str
    side: Literal["BUY", "SELL"]
    quantity: int = Field(..., ge=1)
    order_type: Literal["MARKET", "LIMIT"] = "MARKET"
    limit_price: Optional[float] = None

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
