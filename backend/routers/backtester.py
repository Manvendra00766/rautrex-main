from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from services.backtester_service import run_backtest_logic
from services.validation_service import validate_financial_metrics
from dependencies import get_current_user

router = APIRouter()

class BacktestRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    strategy_type: str
    strategy_params: Dict[str, Any] = Field(default_factory=dict)
    initial_capital: float = 10000.0
    commission: float = 0.1 # 0.1% per trade
    position_sizing: str = "fixed"

@router.post("/run")
async def run_backtest(
    req: BacktestRequest, 
    current_user = Depends(get_current_user)
):
    try:
        results = await run_backtest_logic(
            ticker=req.ticker,
            start_date=req.start_date,
            end_date=req.end_date,
            strategy_type=req.strategy_type,
            strategy_params=req.strategy_params,
            initial_capital=req.initial_capital,
            commission=req.commission,
            position_sizing=req.position_sizing,
            user_id=current_user.id
        )
        results["validation"] = validate_financial_metrics(results)
        return results
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
