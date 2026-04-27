from fastapi import APIRouter, Depends, HTTPException
from supabase_client import supabase
from services import db_service
from services.portfolio_engine import create_transaction, get_portfolio_overview
from pydantic import BaseModel
from dependencies import get_current_user
from typing import Optional, List

router = APIRouter(prefix="/api/v1/users", tags=["users"])

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None

class PortfolioCreate(BaseModel):
    name: str
    description: Optional[str] = None

class PositionAdd(BaseModel):
    ticker: str
    exchange: str
    shares: float
    avg_cost: float

@router.get("/me")
async def get_my_profile(current_user = Depends(get_current_user)):
    response = supabase.table("profiles").select("*").eq("id", current_user.id).single().execute()
    return response.data

@router.patch("/me")
async def update_my_profile(profile: ProfileUpdate, current_user = Depends(get_current_user)):
    data = profile.model_dump(exclude_unset=True)
    response = supabase.table("profiles").update(data).eq("id", current_user.id).execute()
    return response.data

@router.get("/me/portfolios")
async def get_my_portfolios(current_user = Depends(get_current_user)):
    response = await db_service.get_portfolios(current_user.id)
    return response.data

@router.post("/me/portfolios")
async def create_my_portfolio(portfolio: PortfolioCreate, current_user = Depends(get_current_user)):
    response = await db_service.create_portfolio(current_user.id, portfolio.name, portfolio.description)
    return response.data

@router.delete("/me/portfolios/{portfolio_id}")
async def delete_my_portfolio(portfolio_id: str, current_user = Depends(get_current_user)):
    response = await db_service.delete_portfolio(portfolio_id, current_user.id)
    return response.data

@router.post("/me/portfolios/{portfolio_id}/positions")
async def add_portfolio_position(
    portfolio_id: str, 
    pos: PositionAdd, 
    current_user = Depends(get_current_user)
):
    # Verify portfolio belongs to user
    p_check = supabase.table("portfolios").select("user_id").eq("id", portfolio_id).single().execute()
    if not p_check.data or p_check.data['user_id'] != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    try:
        if pos.shares <= 0:
            raise HTTPException(status_code=400, detail="Shares must be positive")
        if pos.avg_cost <= 0:
            raise HTTPException(status_code=400, detail="Average cost price must be positive")
        if pos.avg_cost > 100000:
            raise HTTPException(status_code=400, detail="Average cost price must be per-share, not total value")

        await create_transaction(
            current_user.id,
            portfolio_id,
            "BUY",
            symbol=pos.ticker,
            quantity=pos.shares,
            price=pos.avg_cost,
            gross_amount=pos.shares * pos.avg_cost,
            fees=0.0,
            metadata={"exchange": pos.exchange, "source": "position_add"},
        )
        overview = await get_portfolio_overview(current_user.id, portfolio_id)
        return {
            "ok": True,
            "portfolio_id": portfolio_id,
            "position_added": pos.ticker.upper(),
            "overview": overview,
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/me/backtests")
async def get_my_backtests(current_user = Depends(get_current_user)):
    response = await db_service.get_backtests(current_user.id)
    return response.data

@router.get("/me/notifications")
async def get_my_notifications(limit: int = 20, offset: int = 0, current_user = Depends(get_current_user)):
    response = await db_service.get_notifications(current_user.id, limit, offset)
    return response.data

@router.post("/me/notifications/read-all")
async def mark_notifications_read(current_user = Depends(get_current_user)):
    response = await db_service.mark_all_read(current_user.id)
    return response.data

@router.get("/me/watchlists")
async def get_my_watchlists(current_user = Depends(get_current_user)):
    response = await db_service.get_watchlists(current_user.id)
    return response.data

@router.get("/me/signals")
async def get_my_signals(current_user = Depends(get_current_user)):
    response = await db_service.get_saved_signals(current_user.id)
    return response.data

@router.get("/me/alerts")
async def get_my_alerts(current_user = Depends(get_current_user)):
    response = await db_service.get_price_alerts(current_user.id)
    return response.data
