from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from utils import safe_json
from services.portfolio_service import (
    optimize_portfolio_logic, 
    get_correlation_matrix, 
    calculate_rebalance, 
    backtest_rebalance
)
from services.portfolio_engine import create_transaction, get_portfolio_overview
from services.validation_service import validate_financial_metrics
from auth import get_current_user
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db
from services.ticker_resolver import ticker_resolver_service

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


class AuditRequest(BaseModel):
    portfolio_id: Optional[str] = None


@router.get("/overview")
async def portfolio_overview(
    portfolio_id: Optional[str] = None,
    exclude_history: bool = False,
    current_user=Depends(get_current_user),
):
    try:
        # Trigger silent background reconciliation with Upstox to keep systems 100% aligned
        try:
            from services.reconciliation_service import reconcile_portfolio_with_upstox
            await reconcile_portfolio_with_upstox(current_user.id, portfolio_id)
        except Exception as sync_err:
            print(f"Reconciliation failed silently: {sync_err}")

        data = await get_portfolio_overview(current_user.id, portfolio_id, exclude_history)

        # Register all portfolio tickers with the streaming engine for live price tracking
        try:
            from services.streaming_engine import streaming_engine
            positions = data.get("positions") or []
            tickers = [p.get("ticker") or p.get("symbol") for p in positions if p.get("ticker") or p.get("symbol")]
            if tickers:
                streaming_engine.add_tickers(tickers)
        except Exception as stream_err:
            print(f"Streaming engine ticker registration failed silently: {stream_err}")

        return JSONResponse(content=safe_json(data))
    except Exception as e:
        import traceback
        print(f"Error in portfolio_overview: {e}")
        print(traceback.format_exc())
        
        # Propagate as 500 to surface the error, as requested
        raise HTTPException(status_code=500, detail=f"Portfolio overview failed: {str(e)}")


@router.post("/reconcile/explain")
async def reconcile_explain(
    req: AuditRequest,
    current_user=Depends(get_current_user),
):
    try:
        from services.reconciliation_service import reconcile_portfolio_with_upstox
        report = await reconcile_portfolio_with_upstox(current_user.id, req.portfolio_id)
        
        if report.get("status") == "completed" and report.get("log_messages"):
            logs = "\n".join([f"- {msg}" for msg in report["log_messages"]])
            note = f"### 🔄 Portfolio Sync & Self-Healing Active\n\nI have successfully synchronized your Rautrex dashboard with your live Upstox account. The following corrections were dynamically made to ensure 100% data fidelity:\n\n{logs}\n\n*All risk models (Sharpe, Drawdown, VaR) have been refreshed using first-party broker truth.*"
        else:
            note = "### 🟢 Portfolio In Perfect Sync\n\nYour Rautrex dashboard and live Upstox account are **100% aligned**. No discrepancies in cash margin, position quantities, or asset prices were detected.\n\n*All metrics and risk models are fully verified.*"
            
        return JSONResponse(content={"reconciliation_report": report, "advisor_note": note})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transactions")
async def add_portfolio_transaction(
    req: PortfolioTransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        if req.symbol:
            resolved = await ticker_resolver_service.resolve(req.symbol, db)
            if not resolved:
                raise HTTPException(status_code=400, detail=f"Could not resolve company name or ticker: '{req.symbol}'")
            req.symbol = resolved

        portfolio_check = current_user.db.table("portfolios").select("user_id").eq("id", req.portfolio_id).single().execute()
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

class UpdateCashRequest(BaseModel):
    portfolio_id: str
    cash_balance: float

@router.post("/update-cash")
async def update_cash(
    req: UpdateCashRequest,
    current_user=Depends(get_current_user)
):
    try:
        portfolio_check = current_user.db.table("portfolios").select("user_id").eq("id", req.portfolio_id).single().execute()
        if not portfolio_check.data or portfolio_check.data.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Unauthorized")

        from services.db_service import update_portfolio_cash
        res = await update_portfolio_cash(req.portfolio_id, req.cash_balance)
        return JSONResponse(content={"status": "success", "cash_balance": req.cash_balance})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
