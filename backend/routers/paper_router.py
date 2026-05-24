from fastapi import APIRouter, Depends, HTTPException
from typing import List
from schemas.paper_trading_schema import PlaceOrderRequest, Order, Portfolio
from services.paper_trading_service import paper_trading_service
from auth import get_current_user

router = APIRouter()

@router.get("/portfolio", response_model=Portfolio)
async def get_portfolio(current_user = Depends(get_current_user)):
    """Get the current paper trading portfolio and cash balance"""
    try:
        return await paper_trading_service.get_portfolio(current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/order", response_model=Order)
async def place_order(order_req: PlaceOrderRequest, current_user = Depends(get_current_user)):
    """Place a simulated BUY or SELL order"""
    try:
        return await paper_trading_service.execute_order(order_req, current_user.id)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/orders", response_model=List[Order])
async def get_orders(current_user = Depends(get_current_user)):
    """Get the history of orders for the user"""
    try:
        return paper_trading_service.get_orders(current_user.id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
async def reset_account(current_user = Depends(get_current_user)):
    """Reset the paper trading account to starting balance"""
    try:
        paper_trading_service.reset_account(current_user.id)
        return {"status": "success", "message": "Account reset to starting balance"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
