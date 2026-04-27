from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from services.options_service import price_option, fetch_options_chain, calculate_strategy_pnl, generate_iv_surface
from dependencies import get_current_user

import traceback

router = APIRouter()

class OptionPriceRequest(BaseModel):
    model: str = "black_scholes"
    option_type: str = "call"
    S: float
    K: float
    T: float
    r: float = 0.05
    sigma: float = 0.2
    heston_params: Optional[Dict[str, float]] = None

class StrategyLeg(BaseModel):
    type: str # call, put, stock
    strike: float
    premium: float
    position: int # 1 for long, -1 for short

class StrategyRequest(BaseModel):
    strategy_name: str
    spot: float
    legs: List[StrategyLeg]

@router.post("/price")
async def get_option_price(
    req: OptionPriceRequest, 
    current_user = Depends(get_current_user)
):
    try:
        res = await price_option(req.model, req.option_type, req.S, req.K, req.T, req.r, req.sigma, req.heston_params)
        return res
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chain/{ticker}")
async def get_chain(
    ticker: str, 
    current_user = Depends(get_current_user)
):
    try:
        res = await fetch_options_chain(ticker)
        return res
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategy")
async def get_strategy_pnl(
    req: StrategyRequest, 
    current_user = Depends(get_current_user)
):
    try:
        res = await calculate_strategy_pnl(req.strategy_name, req.spot, [leg.dict() for leg in req.legs])
        return res
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/iv-surface/{ticker}")
async def get_iv_surface(
    ticker: str, 
    current_user = Depends(get_current_user)
):
    try:
        res = await generate_iv_surface(ticker)
        return res
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))