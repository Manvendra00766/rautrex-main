from fastapi import APIRouter, Depends
from typing import List
from schemas.paper_trading_schema import PlaceOrderRequest, Order, Portfolio
from services.paper_trading_service import paper_trading_service
from auth import get_current_user

router = APIRouter()

@router.post("/order", response_model=Order)
async def place_order(order_req: PlaceOrderRequest, current_user = Depends(get_current_user)):
    """Place a paper trading order."""
    return await paper_trading_service.execute_order(order_req, current_user.id)

@router.get("/portfolio", response_model=Portfolio)
async def get_portfolio(current_user = Depends(get_current_user)):
    """Get the paper trading portfolio."""
    return await paper_trading_service.get_portfolio(current_user.id)

@router.get("/orders", response_model=List[Order])
async def get_orders(current_user = Depends(get_current_user)):
    """Get the list of paper trading orders."""
    return paper_trading_service.get_orders(current_user.id)

@router.post("/reset")
async def reset_account(current_user = Depends(get_current_user)):
    """Reset the paper trading account."""
    paper_trading_service.reset_account(current_user.id)
    return {"message": "Account reset to ₹10L", "cash": 1000000.0}
