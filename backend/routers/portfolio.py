from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from supabase_client import supabase
from utils import safe_json
from services.portfolio_service import (
    optimize_portfolio_logic, 
    get_correlation_matrix, 
    calculate_rebalance, 
    backtest_rebalance
)
from services.portfolio_engine import create_transaction, get_portfolio_overview
from services.validation_service import validate_financial_metrics
from dependencies import get_current_user

router = APIRouter()

class OptimizationRequest(BaseModel):
    tickers: List[str]
    method: str = "markowitz"
    objective: str = "max_sharpe"
    constraints: Optional[Dict[str, Any]] = None
    risk_free_rate: float = 0.065

class Position(BaseModel):
    ticker: str
    shares: float

class RebalanceRequest(BaseModel):
    current_positions: List[Position]
    target_weights: Dict[str, float]
    threshold: float = 0.05
    total_value: Optional[float] = None

class RebalanceBacktestRequest(BaseModel):
    tickers: List[str]
    target_weights: Dict[str, float]
    frequency: str = "monthly"
    start_date: str = "2020-01-01"
    initial_capital: float = 100000


class PortfolioTransactionCreate(BaseModel):
    portfolio_id: str
    transaction_type: str
    symbol: Optional[str] = None
    quantity: Optional[float] = None
    price: Optional[float] = None
    gross_amount: Optional[float] = None
    fees: float = 0.0
    executed_at: Optional[str] = None
    lot_method: str = "FIFO"
    metadata: Dict[str, Any] = {}
    external_id: Optional[str] = None


@router.get("/overview")
async def portfolio_overview(
    portfolio_id: Optional[str] = None,
    current_user=Depends(get_current_user),
):
    try:
        data = await get_portfolio_overview(current_user.id, portfolio_id)
        return JSONResponse(content=safe_json(data))
    except Exception as e:
        import traceback
        print(f"Error in portfolio_overview: {e}")
        print(traceback.format_exc())
        
        # Fallback response as requested by user to prevent 500 crashes
        fallback = {
            "nav": 0.0,
            "cash_balance": 0.0,
            "daily_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "holdings": [],
            "history": [],
            "portfolio": None,
            "summary": None,
            "positions": [],
            "equity_curve": [],
            "allocation": {"by_sector": [], "by_asset_type": [], "by_country": []},
            "warnings": [],
        }
        return JSONResponse(content=safe_json(fallback))


@router.post("/transactions")
async def add_portfolio_transaction(
    req: PortfolioTransactionCreate,
    current_user=Depends(get_current_user),
):
    try:
        portfolio_check = supabase.table("portfolios").select("user_id").eq("id", req.portfolio_id).single().execute()
        if not portfolio_check.data or portfolio_check.data.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        transaction = await create_transaction(
            current_user.id,
            req.portfolio_id,
            req.transaction_type,
            symbol=req.symbol,
            quantity=req.quantity,
            price=req.price,
            gross_amount=req.gross_amount,
            fees=req.fees,
            executed_at=req.executed_at,
            lot_method=req.lot_method,
            metadata=req.metadata,
            external_id=req.external_id,
        )
        overview = await get_portfolio_overview(current_user.id, req.portfolio_id)
        return JSONResponse(content=safe_json({"transaction": transaction, "overview": overview}))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/optimize")
async def optimize_portfolio(
    req: OptimizationRequest, 
    current_user = Depends(get_current_user)
):
    if not req.tickers:
        raise HTTPException(status_code=400, detail="Provide at least one ticker")
    try:
        res = await optimize_portfolio_logic(
            req.tickers, req.method, req.objective, req.constraints, req.risk_free_rate
        )
        res["validation"] = validate_financial_metrics(res)
        return JSONResponse(content=safe_json(res))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/corr-matrix")
async def corr_matrix(
    tickers: str, 
    current_user = Depends(get_current_user)
):
    ticker_list = tickers.split(",")
    try:
        res = await get_correlation_matrix(ticker_list)
        return JSONResponse(content=safe_json({"correlation_matrix": res}))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rebalance")
async def rebalance_portfolio(
    req: RebalanceRequest, 
    current_user = Depends(get_current_user)
):
    try:
        res = await calculate_rebalance(
            [p.dict() for p in req.current_positions],
            req.target_weights,
            req.threshold,
            req.total_value
        )
        return JSONResponse(content=safe_json(res))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rebalance/backtest")
async def backtest_rebalance_route(
    req: RebalanceBacktestRequest, 
    current_user = Depends(get_current_user)
):
    try:
        res = await backtest_rebalance(
            req.tickers,
            req.target_weights,
            req.frequency,
            req.start_date,
            req.initial_capital
        )
        return JSONResponse(content=safe_json(res))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
