import asyncio
import yfinance as yf
from typing import List, Optional, Dict
from fastapi import HTTPException
from datetime import datetime
from schemas.paper_trading_schema import PlaceOrderRequest, Order, Position, Portfolio
from supabase_client import supabase
from core.logger import logger

STARTING_CASH = 1_000_000.0

class PaperTradingService:
    def fetch_price(self, ticker: str) -> float:
        """Fetch current price using multi-source pricing engine (with yfinance fallback)"""
        # Try Upstox API first for Indian assets via the pricing engine
        is_indian = ticker.endswith(".NS") or ticker.endswith(".BO") or "GS" in ticker or "GB" in ticker
        if is_indian:
            try:
                import asyncio
                from services.pricing_engine import get_batch_price_snapshots
                
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                price_map = loop.run_until_complete(get_batch_price_snapshots([ticker]))
                snap = price_map.get(ticker)
                if snap and snap.last_price > 0:
                    return float(snap.last_price)
            except Exception as upstox_err:
                logger.warning(f"Upstox quote fetch failed for {ticker}: {upstox_err}. Falling back to yfinance.")

        try:
            stock = yf.Ticker(ticker)
            # Try various ways to get price from fast_info
            info = stock.fast_info
            price = None
            
            # fast_info can be a dict or an object depending on version/mock
            if hasattr(info, 'get'):
                price = info.get('lastPrice') or info.get('last_price')
            
            if price is None and hasattr(info, 'last_price'):
                price = info.last_price

            if price is None:
                # Fallback to history
                hist = stock.history(period="1d")
                if not hist.empty:
                    price = hist['Close'].iloc[-1]
            
            if price is None or not isinstance(price, (int, float)):
                raise ValueError("Price not found")
            return float(price)
        except Exception as e:
            if isinstance(e, HTTPException): raise e
            logger.error(f"Failed to fetch price for {ticker}: {e}")
            raise HTTPException(status_code=400, detail=f"Could not fetch price for {ticker}")

    def get_or_create_account(self, user_id: str):
        """Get paper trading account or create one with starting cash"""
        try:
            response = supabase.table("paper_accounts").select("*").eq("user_id", user_id).execute()
            if response.data:
                return response.data[0]
            
            # Create new account
            data = {"user_id": user_id, "cash_balance": STARTING_CASH}
            response = supabase.table("paper_accounts").insert(data).execute()
            return response.data[0]
        except Exception as e:
            logger.error(f"Account error for {user_id}: {e}")
            raise HTTPException(status_code=500, detail="Database error accessing paper account")

    async def execute_order(self, order_req: PlaceOrderRequest, user_id: str) -> Order:
        """Execute a buy or sell order and update positions/cash"""
        # 1. Fetch current price
        price = self.fetch_price(order_req.ticker)
        
        # 2. Get account
        account = self.get_or_create_account(user_id)
        cash_balance = account["cash_balance"]
        
        order_status = "EXECUTED"
        total_cost = price * order_req.quantity
        
        # 3 & 4. Validations
        if order_req.side == "BUY":
            if cash_balance < total_cost:
                order_status = "REJECTED"
        else: # SELL
            pos_resp = supabase.table("paper_positions") \
                .select("*").eq("user_id", user_id).eq("ticker", order_req.ticker).execute()
            if not pos_resp.data or pos_resp.data[0]["quantity"] < order_req.quantity:
                order_status = "REJECTED"

        # 5. Insert order
        order_data = {
            "user_id": user_id,
            "ticker": order_req.ticker,
            "side": order_req.side,
            "quantity": order_req.quantity,
            "order_type": order_req.order_type,
            "limit_price": order_req.limit_price,
            "executed_price": price if order_status == "EXECUTED" else None,
            "status": order_status,
            "created_at": datetime.now().isoformat()
        }
        order_insert = supabase.table("paper_orders").insert(order_data).execute()
        saved_order = order_insert.data[0]

        if order_status == "REJECTED":
            return Order(**saved_order)

        # 6 & 7. Update Position
        if order_req.side == "BUY":
            pos_resp = supabase.table("paper_positions") \
                .select("*").eq("user_id", user_id).eq("ticker", order_req.ticker).execute()
            
            if pos_resp.data:
                old_pos = pos_resp.data[0]
                new_qty = old_pos["quantity"] + order_req.quantity
                new_avg = (old_pos["quantity"] * old_pos["avg_buy_price"] + total_cost) / new_qty
                supabase.table("paper_positions").update({
                    "quantity": new_qty,
                    "avg_buy_price": new_avg
                }).eq("id", old_pos["id"]).execute()
            else:
                supabase.table("paper_positions").insert({
                    "user_id": user_id,
                    "ticker": order_req.ticker,
                    "quantity": order_req.quantity,
                    "avg_buy_price": price
                }).execute()
            
            # 8. Update cash
            new_cash = cash_balance - total_cost
            supabase.table("paper_accounts").update({"cash_balance": new_cash}).eq("user_id", user_id).execute()
            
        else: # SELL
            old_pos = pos_resp.data[0]
            new_qty = old_pos["quantity"] - order_req.quantity
            
            if new_qty == 0:
                supabase.table("paper_positions").delete().eq("id", old_pos["id"]).execute()
            else:
                supabase.table("paper_positions").update({"quantity": new_qty}).eq("id", old_pos["id"]).execute()
                
            # Update cash
            new_cash = cash_balance + total_cost
            supabase.table("paper_accounts").update({"cash_balance": new_cash}).eq("user_id", user_id).execute()

        return Order(**saved_order)

    async def get_portfolio(self, user_id: str) -> Portfolio:
        """Fetch account and all positions with current values"""
        account = self.get_or_create_account(user_id)
        pos_resp = supabase.table("paper_positions").select("*").eq("user_id", user_id).execute()
        db_positions = pos_resp.data
        
        if not db_positions:
            return Portfolio(
                cash_balance=account["cash_balance"],
                total_invested=0,
                total_current_value=0,
                total_pnl=0,
                total_pnl_pct=0,
                positions=[]
            )

        # Concurrent price fetching
        async def fetch_and_map(p):
            # Run blocking fetch_price in thread
            curr_price = await asyncio.to_thread(self.fetch_price, p["ticker"])
            qty = p["quantity"]
            avg = p["avg_buy_price"]
            total_val = curr_price * qty
            pnl = (curr_price - avg) * qty
            pnl_pct = ((curr_price / avg) - 1) * 100 if avg != 0 else 0
            
            return Position(
                ticker=p["ticker"],
                quantity=qty,
                avg_buy_price=avg,
                current_price=curr_price,
                pnl=pnl,
                pnl_pct=pnl_pct,
                total_value=total_val
            )

        positions = await asyncio.gather(*(fetch_and_map(p) for p in db_positions))
        
        total_invested = sum(p.quantity * p.avg_buy_price for p in positions)
        total_current_value = sum(p.total_value for p in positions)
        total_pnl = total_current_value - total_invested
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested != 0 else 0
        
        return Portfolio(
            cash_balance=account["cash_balance"],
            total_invested=total_invested,
            total_current_value=total_current_value,
            total_pnl=total_pnl,
            total_pnl_pct=total_pnl_pct,
            positions=positions
        )

    def get_orders(self, user_id: str) -> List[Order]:
        """Fetch last 50 orders"""
        response = supabase.table("paper_orders") \
            .select("*").eq("user_id", user_id).order("created_at", desc=True).limit(50).execute()
        return [Order(**o) for o in response.data]

    def reset_account(self, user_id: str):
        """Reset everything for the user"""
        supabase.table("paper_positions").delete().eq("user_id", user_id).execute()
        supabase.table("paper_orders").delete().eq("user_id", user_id).execute()
        supabase.table("paper_accounts").update({"cash_balance": STARTING_CASH}).eq("user_id", user_id).execute()

paper_trading_service = PaperTradingService()
