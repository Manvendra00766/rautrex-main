from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

class DCFInput(BaseModel):
    ticker: str = Field(..., example="RELIANCE.NS")
    revenue: list[float] = Field(..., description="Last 3-5 years revenue in INR Cr")
    ebit_margin: float = Field(..., example=0.18)
    tax_rate: float = Field(..., example=0.25)
    capex_pct: float = Field(..., example=0.08)
    da_pct: float = Field(default=0.03, example=0.03)
    nwc_change_pct: float = Field(..., example=0.02)
    wacc: float = Field(..., example=0.12)
    terminal_growth_rate: float = Field(..., example=0.04)
    projection_years: int = Field(default=5, ge=1, le=10)
    shares_outstanding: float = Field(..., description="Shares outstanding in Cr")
    net_debt: float = Field(..., description="Net debt in INR Cr, negative means net cash")
    currency: str = Field(default="USD")
    unit: str = Field(default="Mn")
    unit_label: str = Field(default="$ Mn")
    exchange: str = Field(default="Unknown")
    warnings: list[str] = Field(default_factory=list)
    field_sources: dict[str, str] = Field(default_factory=dict)

    @field_validator('revenue')
    @classmethod
    def validate_revenue_length(cls, v):
        if len(v) < 2:
            raise ValueError("At least 2 years of revenue data required for growth calculation")
        return v

class DCFOutput(BaseModel):
    ticker: str
    intrinsic_value_per_share: float
    current_market_price: Optional[float] = None
    upside_downside_pct: Optional[float] = None
    projected_fcfs: list[float]
    terminal_value: float
    enterprise_value: float
    equity_value: float
    wacc_used: float
    sensitivity_table: dict[str, dict[str, float]]
    valuation_date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    warnings: list[str] = []
    errors: list[str] = []
    data_quality_score: str = "HIGH"
    field_sources: dict[str, str] = {}
    currency: str = "USD"
    unit: str = "Mn"
    unit_label: str = "$ Mn"
    exchange: str = "Unknown"
    market_price_native: float = 0.0

class DCFSaveRequest(BaseModel):
    dcf_input: DCFInput
    dcf_output: DCFOutput

class DCFCompareRequest(BaseModel):
    input_a: DCFInput
    input_b: DCFInput

class DCFCompareResponse(BaseModel):
    winner: str  # ticker or "equal"
    upside_difference_pct: float
    output_a: DCFOutput
    output_b: DCFOutput
