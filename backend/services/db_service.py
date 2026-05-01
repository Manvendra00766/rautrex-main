from supabase_client import supabase
from datetime import datetime
from fastapi import HTTPException

# --- PROFILES ---

async def get_profile(user_id: str):
    return supabase.table("profiles").select("*").eq("id", user_id).single().execute()

async def update_profile(user_id: str, data: dict):
    # Allowed fields: full_name, avatar_url, preferences
    return supabase.table("profiles").update(data).eq("id", user_id).execute()

# --- PORTFOLIOS ---

async def get_portfolios(user_id: str):
    return supabase.table("portfolios").select("*, portfolio_positions(*)").eq("user_id", user_id).execute()

async def create_portfolio(user_id: str, name: str, strategy: str = "Equity", cash_balance: float = 0, description: str = None):
    existing = supabase.table("portfolios").select("id").eq("user_id", user_id).limit(1).execute()
    is_default = not bool(existing.data)
    
    return supabase.table("portfolios").insert({
        "user_id": user_id, 
        "name": name, 
        "strategy": strategy,
        "description": description,
        "cash_balance": cash_balance,
        "is_default": is_default,
    }).execute()

async def delete_portfolio(portfolio_id: str, user_id: str):
    return supabase.table("portfolios").delete().eq("id", portfolio_id).eq("user_id", user_id).execute()

async def add_position(portfolio_id: str, ticker: str, exchange: str, shares: float, avg_cost_price: float):
   if shares <= 0:
       raise ValueError("Shares must be positive")
   if avg_cost_price <= 0:
       raise ValueError("Average cost price must be positive")
   if avg_cost_price > 100000:
       raise ValueError("avg_cost must be per share price, not total value")

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
            "triggered_at": datetime.now().isoformat()
        }) \
        .eq("id", alert_id) \
        .execute()

async def get_price_alerts(user_id: str):
    return supabase.table("price_alerts").select("*").eq("user_id", user_id).execute()

# --- SIGNALS ---

async def save_signal(user_id: str, ticker: str, signal_type: str, details: dict):
    return supabase.table("saved_signals").insert({
        "user_id": user_id, "ticker": ticker.upper(), 
        "signal_type": signal_type, "details": details
    }).execute()

async def get_saved_signals(user_id: str):
    return supabase.table("saved_signals").select("*").eq("user_id", user_id).execute()
