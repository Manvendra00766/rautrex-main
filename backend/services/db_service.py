from supabase_client import supabase
from datetime import datetime, timezone
import asyncio
from fastapi import HTTPException

# --- PROFILES ---

async def get_profile(user_id: str):
    return supabase.table("profiles").select("*").eq("id", user_id).single().execute()

async def update_profile(user_id: str, data: dict):
    # Allowed fields: full_name, avatar_url, preferences
    return supabase.table("profiles").update(data).eq("id", user_id).execute()

# --- PORTFOLIOS ---

async def get_portfolios(user_id: str):
    return supabase.table("portfolios") \
        .select("*, portfolio_positions(*), transactions(*)") \
        .eq("user_id", user_id).execute()

async def create_portfolio(user_id: str, name: str, strategy: str = "Equity", cash_balance: float = 0, description: str = None, currency: str = "USD"):
    # FIXED: Record initial NAV snapshot on portfolio creation so history charts render instantly with a baseline
    existing = supabase.table("portfolios").select("id").eq("user_id", user_id).limit(1).execute()
    is_default = not bool(existing.data)
    
    res = supabase.table("portfolios").insert({
        "user_id": user_id, 
        "name": name, 
        "strategy": strategy,
        "description": description,
        "cash_balance": cash_balance,
        "initial_cash": cash_balance,
        "is_default": is_default,
        "base_currency": currency,
    }).execute()
    
    if res.data:
        portfolio_id = res.data[0]['id']
        try:
            today = datetime.now(tz=timezone.utc).date().isoformat()
            supabase.table("historical_equity").insert({
                "user_id": user_id,
                "portfolio_id": portfolio_id,
                "snapshot_date": today,
                "nav": cash_balance,
                "cash_balance": cash_balance,
                "market_value": 0.0,
                "daily_pnl": 0.0,
                "gross_exposure": 0.0,
                "net_exposure": 0.0,
            }).execute()
        except Exception as e:
            print(f"Failed to record initial historical equity: {e}")
            
    return res

async def delete_portfolio(portfolio_id: str, user_id: str):
    return supabase.table("portfolios").delete().eq("id", portfolio_id).eq("user_id", user_id).execute()

async def get_portfolio_by_id(portfolio_id: str):
    try:
        response = supabase.table("portfolios").select("*").eq("id", portfolio_id).limit(1).execute()
        return response.data[0] if response.data else None
    except Exception:
        return None

async def update_portfolio_cash(portfolio_id: str, new_cash_balance: float):
    if new_cash_balance < 0:
        raise ValueError("Cash balance cannot be negative")
    return supabase.table("portfolios") \
        .update({"cash_balance": new_cash_balance}) \
        .eq("id", portfolio_id) \
        .execute()

async def record_transaction(portfolio_id: str, ticker: str, transaction_type: str, shares: float, price_per_share: float, notes: str = None):
    if transaction_type not in ["BUY", "SELL"]:
        raise ValueError("transaction_type must be BUY or SELL")
    if shares <= 0:
        raise ValueError("Shares must be positive")
    if price_per_share <= 0:
        raise ValueError("Price per share must be positive")

    return supabase.table("transactions").insert({
        "portfolio_id": portfolio_id,
        "ticker": ticker.upper(),
        "transaction_type": transaction_type.upper(),
        "shares": shares,
        "price_per_share": price_per_share,
        "notes": notes,
    }).execute()

async def get_transactions(portfolio_id: str, limit: int = 50, offset: int = 0):
    return supabase.table("transactions") \
        .select("*") \
        .eq("portfolio_id", portfolio_id) \
        .order("created_at", ascending=False) \
        .range(offset, offset + limit - 1) \
        .execute()

async def add_position(portfolio_id: str, ticker: str, exchange: str, shares: float, avg_cost_price: float):
   if shares <= 0:
       raise ValueError("Shares must be positive")
   if avg_cost_price <= 0:
       raise ValueError("Average cost price must be positive")
   if avg_cost_price > 100000:
       raise ValueError("avg_cost must be per share price, not total value")

   existing = supabase.table("portfolio_positions") \
        .select("id") \
        .eq("portfolio_id", portfolio_id) \
        .eq("ticker", ticker.upper()) \
        .limit(1).execute()
    
   if existing.data:
        raise HTTPException(status_code=409, detail=f"{ticker.upper()} already exists in this portfolio. Use update position instead.")

   return supabase.table("portfolio_positions").insert({        
        "portfolio_id": portfolio_id, 
        "ticker": ticker.upper(),
        "exchange": exchange.upper(),
        "shares": shares, 
        "avg_cost_price": avg_cost_price,
    }).execute()



# --- WATCHLISTS ---

async def get_watchlists(user_id: str):
    return supabase.table("watchlists").select("*, watchlist_items(*)").eq("user_id", user_id).execute()

async def create_watchlist(user_id: str, name: str):
    return supabase.table("watchlists").insert({"user_id": user_id, "name": name}).execute()

async def add_watchlist_item(watchlist_id: str, ticker: str):
    try:
        return supabase.table("watchlist_items").insert({
            "watchlist_id": watchlist_id, 
            "ticker": ticker.upper()
        }).execute()
    except Exception as e:
        # Check for unique constraint violation in a real app, 
        # but here we follow the test requirement to raise 409
        if "unique" in str(e).lower() or "already exists" in str(e).lower():
            raise HTTPException(status_code=409, detail="Ticker already in watchlist")
        raise e

async def get_watchlist_items(watchlist_id: str):
    return supabase.table("watchlist_items") \
        .select("*") \
        .eq("watchlist_id", watchlist_id) \
        .order("added_at", ascending=True) \
        .execute()

# --- BACKTESTS ---

async def save_backtest(user_id: str, name: str, ticker: str, strategy: str, params: dict, results: dict):
    return supabase.table("saved_backtests").insert({
        "user_id": user_id, 
        "name": name, 
        "ticker": ticker,
        "strategy": strategy, 
        "params": params, 
        "results": results
    }).execute()

async def get_backtests(user_id: str, limit: int = 10, offset: int = 0):
    return supabase.table("saved_backtests") \
        .select("*") \
        .eq("user_id", user_id) \
        .range(offset, offset + limit - 1) \
        .execute()

async def toggle_favorite(backtest_id: str, user_id: str, is_favorite: bool):
    return supabase.table("saved_backtests") \
        .update({"is_favorite": is_favorite}) \
        .eq("id", backtest_id) \
        .eq("user_id", user_id) \
        .execute()

async def delete_backtest(backtest_id: str, user_id: str):
    return supabase.table("saved_backtests") \
        .delete() \
        .eq("id", backtest_id) \
        .eq("user_id", user_id) \
        .execute()

# --- NOTIFICATIONS ---

async def create_notification(user_id: str, type: str, title: str, body: str, metadata: dict = None):
    valid_types = ["signal", "alert", "portfolio", "system", "risk"]
    if type not in valid_types:
        raise ValueError(f"Invalid notification type: {type}")
        
    return supabase.table("notifications").insert({
        "user_id": user_id,
        "type": type,
        "title": title,
        "body": body,
        "metadata": metadata or {},
        "is_read": False
    }).execute()

async def get_notifications(user_id: str, limit: int = 20, offset: int = 0):
    return supabase.table("notifications").select("*") \
        .eq("user_id", user_id) \
        .order("is_read", ascending=True) \
        .order("created_at", ascending=False) \
        .range(offset, offset + limit - 1).execute()

async def get_unread_count(user_id: str):
    res = supabase.table("notifications") \
        .select("*", count="exact") \
        .eq("user_id", user_id) \
        .eq("is_read", False) \
        .execute()
    return res.count if res.count is not None else 0

async def mark_read(notification_id: str, user_id: str):
    return supabase.table("notifications") \
        .update({"is_read": True}) \
        .eq("id", notification_id) \
        .eq("user_id", user_id) \
        .execute()

async def mark_all_read(user_id: str):
    return supabase.table("notifications") \
        .update({"is_read": True}) \
        .eq("user_id", user_id) \
        .eq("is_read", False) \
        .execute()

# --- PRICE ALERTS ---

async def create_price_alert(user_id: str, ticker: str, target_price: float, condition: str):
    if condition not in ["above", "below", "crosses"]:
        raise ValueError(f"Invalid alert condition: {condition}")
        
    return supabase.table("price_alerts").insert({
        "user_id": user_id, 
        "ticker": ticker.upper(), 
        "target_price": target_price, 
        "condition": condition,
        "is_triggered": False
    }).execute()

async def get_active_alerts():
    return supabase.table("price_alerts") \
        .select("*") \
        .eq("is_triggered", False) \
        .execute()

async def trigger_alert(alert_id: str):
    return supabase.table("price_alerts") \
        .update({
            "is_triggered": True, 
            "triggered_at": datetime.now(timezone.utc).isoformat()
        }) \
        .eq("id", alert_id) \
        .execute()

async def get_price_alerts(user_id: str):
    return supabase.table("price_alerts").select("*").eq("user_id", user_id).execute()

# --- SIGNALS ---

async def save_signal(user_id: str, ticker: str, signal_type: str, details: dict):
    return supabase.table("saved_signals").insert({
        "user_id": user_id, 
        "ticker": ticker.upper(), 
        "signal_type": signal_type, 
        "details": details,
        "created_at": datetime.now(timezone.utc).isoformat()
    }).execute()

async def get_saved_signals(user_id: str):
    return supabase.table("saved_signals").select("*").eq("user_id", user_id).execute()

# --- IMPORTED BROKER PORTFOLIOS ---

async def save_imported_portfolio(user_id: str, broker: str, holdings: list, analysis: dict):
    """
    Saves the imported broker portfolio in two places:
    1. Rich JSON data and analysis in the user's profile preferences
    2. A standard user portfolio in the portfolios table so it integrates with standard tools
    """
    # 1. Save rich JSON and analysis in user profile preferences
    try:
        profile_res = await get_profile(user_id)
        preferences = {}
        if profile_res.data:
            profile_data = profile_res.data
            profile = profile_data[0] if isinstance(profile_data, list) else profile_data
            preferences = profile.get("preferences") or {}
        
        preferences["imported_portfolio"] = {
            "broker": broker,
            "holdings": holdings,
            "analysis": analysis,
            "synced_at": datetime.now(tz=timezone.utc).isoformat()
        }
        await update_profile(user_id, {"preferences": preferences})
    except Exception as e:
        print(f"Failed to update profile preferences with imported portfolio: {e}")
        
    # 2. Save as standard portfolio in portfolios table
    try:
        portfolio_name = f"{broker.capitalize()} Portfolio"
        existing = supabase.table("portfolios").select("id").eq("user_id", user_id).eq("name", portfolio_name).execute()
        
        # Determine currency based on broker
        currency = "INR" if broker.lower() in ["upstox", "zerodha", "groww", "cas_statement"] else "USD"
        
        if existing.data:
            portfolio_id = existing.data[0]["id"]
            # Clear old positions and transactions
            try:
                supabase.table("portfolio_positions").delete().eq("portfolio_id", portfolio_id).execute()
            except Exception as del_err:
                print(f"Failed to clear old positions: {del_err}")
                
            try:
                supabase.table("transactions").delete().eq("portfolio_id", portfolio_id).execute()
            except Exception as del_tx_err:
                print(f"Failed to clear old transactions: {del_tx_err}")
                
            # Update cash balance, initial_cash, description and base_currency
            supabase.table("portfolios").update({
                "cash_balance": float(analysis.get("cash_balance") or 0.0),
                "initial_cash": float(analysis.get("cash_balance") or 0.0),
                "description": f"Imported portfolio from {broker.capitalize()}.",
                "base_currency": currency
            }).eq("id", portfolio_id).execute()
        else:
            res = await create_portfolio(
                user_id=user_id,
                name=portfolio_name,
                strategy="Imported",
                cash_balance=float(analysis.get("cash_balance") or 0.0),
                description=f"Imported portfolio from {broker.capitalize()}.",
                currency=currency
            )
            if res.data:
                portfolio_id = res.data[0]["id"]
            else:
                return
                
        # Insert all positions
        positions_to_insert = []
        for h in holdings:
            shares = float(h.get("shares") or h.get("units") or 0.0)
            avg_cost = float(h.get("avg_cost") or h.get("avg_cost_price") or 0.0)
            ticker = str(h.get("ticker") or h.get("name") or "").upper()
            if shares > 0 and avg_cost > 0 and ticker:
                positions_to_insert.append({
                    "portfolio_id": portfolio_id,
                    "ticker": ticker,
                    "exchange": "NSE",
                    "shares": shares,
                    "avg_cost_price": avg_cost
                })
        
        if positions_to_insert:
            supabase.table("portfolio_positions").insert(positions_to_insert).execute()
            
        # Record today's calculated NAV snapshot in historical_equity
        try:
            today = datetime.now(tz=timezone.utc).date().isoformat()
            nav_val = float(analysis.get("cash_balance") or 0.0) + float(analysis.get("current_value") or 0.0)
            supabase.table("historical_equity").upsert({
                "user_id": user_id,
                "portfolio_id": portfolio_id,
                "snapshot_date": today,
                "nav": nav_val,
                "cash_balance": float(analysis.get("cash_balance") or 0.0),
                "market_value": float(analysis.get("current_value") or 0.0),
                "daily_pnl": float(analysis.get("pnl") or 0.0),
            }).execute()
        except Exception as hist_err:
            print(f"Failed to record daily historical equity snapshot: {hist_err}")
    except Exception as e:
        print(f"Failed to save standard portfolio for imported broker: {e}")

async def get_imported_portfolio(user_id: str):
    """
    Retrieves the imported broker portfolio from user profile preferences.
    """
    try:
        profile_res = await get_profile(user_id)
        if profile_res.data:
            preferences = profile_res.data[0].get("preferences") or {}
            return preferences.get("imported_portfolio")
    except Exception as e:
        print(f"Failed to retrieve imported portfolio: {e}")
    return None

