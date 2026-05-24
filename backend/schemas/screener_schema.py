from pydantic import BaseModel, Field
from typing import Literal, Optional, List

class ScreenerFilterRequest(BaseModel):
    min_pe: Optional[float] = Field(None, ge=0)
    max_pe: Optional[float] = Field(None, ge=0)
    min_roe: Optional[float] = Field(None, ge=0)
    max_roe: Optional[float] = Field(None, ge=0)
    min_rsi: Optional[float] = Field(None, ge=0)
    max_rsi: Optional[float] = Field(None, ge=0)
    min_market_cap: Optional[float] = Field(None, ge=0)
    max_market_cap: Optional[float] = Field(None, ge=0)
    min_dcf_margin_of_safety: Optional[float] = None

class ScreenerStockResult(BaseModel):
    symbol: str
    company_name: str
    current_price: Optional[float] = None
    pe_ratio: Optional[float] = None
    roe: Optional[float] = None
    rsi: Optional[float] = None
    market_cap: Optional[float] = None
    dcf_margin_of_safety: Optional[float] = None
    signal: Literal["STRONG BUY", "BUY", "FAIR", "OVERVALUED", "N/A"]

class ScreenerFilter(BaseModel):
    metric: Literal[
        "pe_ratio",
        "pb_ratio",
        "rsi_14",
        "eps_growth_yoy",
        "revenue_growth_yoy",
        "market_cap_cr",
        "week_52_from_high_pct"
    ]
    operator: Literal["lt", "gt", "lte", "gte"]
    value: float

class ScreenerRequest(BaseModel):
    filters: List[ScreenerFilter] = Field(..., max_length=5)
    universe: Literal["nifty50", "nifty100"] = "nifty50"
    limit: int = Field(default=20, le=50)

class ScreenerResult(BaseModel):
    ticker: str
    company_name: str
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    rsi_14: Optional[float] = None
    eps_growth_yoy: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    market_cap_cr: Optional[float] = None
    week_52_from_high_pct: Optional[float] = None
    current_price: Optional[float] = None

class ScreenerPreset(BaseModel):
    id: str
    name: str
    filters: List[ScreenerFilter]
    user_id: str
