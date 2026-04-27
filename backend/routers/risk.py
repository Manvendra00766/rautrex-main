from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from services.risk_service import (
    calculate_portfolio_risk, 
    run_stress_test, 
    calculate_factors, 
    calculate_portfolio_factors,
    run_scenarios
)
from services.validation_service import validate_financial_metrics
from dependencies import get_current_user

import traceback

router = APIRouter()

class PortfolioItem(BaseModel):
    ticker: str
    weight: float

class RiskRequest(BaseModel):
    portfolio: List[PortfolioItem] = Field(..., min_length=1)
    start_date: str = "2020-01-01"
    end_date: str = "2024-01-01"
    benchmark: str = "^GSPC"
    factors: int = 5 # 3 or 5
    momentum: bool = True

@router.post("/portfolio")
async def get_portfolio_risk(
    req: RiskRequest, 
    current_user = Depends(get_current_user)
):
    # Validate weights sum to 1.0
    weights = [item.weight for item in req.portfolio]
    if abs(sum(weights) - 1.0) > 1e-4:
        raise HTTPException(status_code=400, detail="Portfolio weights must sum to 100%")
        
    try:
        res = await calculate_portfolio_risk(
            [item.dict() for item in req.portfolio],
            req.start_date,
            req.end_date,
            req.benchmark
        )
        res["validation"] = validate_financial_metrics(res)
        return res
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/stress-test")
async def post_stress_test(
    req: RiskRequest, 
    current_user = Depends(get_current_user)
):
    try:
        res = await run_stress_test([item.dict() for item in req.portfolio])
        return res
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/factors/{ticker}")
async def get_factors(
    ticker: str, 
    current_user = Depends(get_current_user)
):
    try:
        res = await calculate_factors(ticker)
        return res
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/factors")
async def post_portfolio_factors(
    req: RiskRequest, 
    current_user = Depends(get_current_user)
):
    try:
        res = await calculate_portfolio_factors(
            [item.dict() for item in req.portfolio],
            req.start_date,
            req.factors,
            req.momentum
        )
        return res
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scenarios")
async def post_scenarios(
    req: RiskRequest, 
    current_user = Depends(get_current_user)
):
    try:
        res = await run_scenarios([item.dict() for item in req.portfolio])
        return res
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))