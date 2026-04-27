from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from services.monte_carlo_service import run_monte_carlo_simulation
from services.validation_service import validate_financial_metrics
from dependencies import get_current_user

router = APIRouter()

class AssetWeight(BaseModel):
    ticker: str
    weight: float

class MonteCarloRequest(BaseModel):
    ticker: Optional[str] = None
    assets: Optional[List[AssetWeight]] = None
    time_horizon: int = 365
    num_simulations: int = 1000
    initial_investment: float = 10000.0
    confidence_level: float = 0.95

@router.post("/run")
async def run_simulation(
    req: MonteCarloRequest, 
    current_user = Depends(get_current_user)
):
    if not req.ticker and not req.assets:
        raise HTTPException(status_code=400, detail="Provide either a ticker or a list of assets with weights")
    
    tickers = [req.ticker] if req.ticker else [a.ticker for a in req.assets]
    weights = [1.0] if req.ticker else [a.weight for a in req.assets]
    
    # Validate weights sum to 1.0 if portfolio
    if req.assets and abs(sum(weights) - 1.0) > 1e-6:
        raise HTTPException(status_code=400, detail="Portfolio weights must sum to 1.0")

    try:
        results = await run_monte_carlo_simulation(
            tickers=tickers,
            weights=weights,
            time_horizon=req.time_horizon,
            num_simulations=req.num_simulations,
            initial_investment=req.initial_investment,
            confidence_level=req.confidence_level
        )
        results["validation"] = validate_financial_metrics(results)
        return results
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal simulation error")