import yfinance as yf
from supabase_client import supabase
from services.notification_service import create_notification
from typing import List, Dict, Any

async def check_price_alerts():
    """
    APScheduler job to check price alerts and create notifications.
    """
    # Fetch all active alerts
    alerts_res = supabase.table("price_alerts").select("*").eq("is_triggered", False).execute()
    alerts = alerts_res.data
    
    if not alerts:
        return

    # Group alerts by ticker to minimize yfinance calls
    tickers = list(set([a['ticker'] for a in alerts]))
    
    try:
        # Fetch current prices
        downloaded = yf.download(tickers, period="1d", progress=False)
        if downloaded.empty or 'Close' not in downloaded.columns:
            return
            
        data = downloaded['Close']
        current_prices = {}
        
        if len(tickers) == 1:
            if not data.empty:
                current_prices[tickers[0]] = float(data.iloc[-1])
        else:
            for t in tickers:
                if t in data.columns:
                    ticker_data = data[t].dropna()
                    if not ticker_data.empty:
                        current_prices[t] = float(ticker_data.iloc[-1])
            
        for alert in alerts:
            ticker = alert['ticker']
            current_price = current_prices.get(ticker)
            if current_price is None:
                continue
                
            condition = alert['condition'] # 'above' or 'below'
            target_price = alert['target_price']
            
            triggered = False
            if condition == 'above' and current_price >= target_price:
                triggered = True
            elif condition == 'below' and current_price <= target_price:
                triggered = True
                
            if triggered:
                # Mark as triggered
                from datetime import datetime
                supabase.table("price_alerts").update({
                    "is_triggered": True,
                    "triggered_at": datetime.now().isoformat()
                }).eq("id", alert['id']).execute()
                
                # Create notification
                await create_notification(
                    user_id=alert['user_id'],
                    type="price_alert",
                    title=f"Price Alert: {ticker}",
                    body=f"{ticker} has moved {condition} your target of {target_price}. Current price: {round(current_price, 2)}",
                    metadata={"ticker": ticker, "target_price": target_price, "current_price": current_price}
                )
    except Exception as e:
        print(f"Error in check_price_alerts: {e}")

async def create_alert(user_id: str, ticker: str, condition: str, target_price: float):
    return supabase.table("price_alerts").insert({
        "user_id": user_id,
        "ticker": ticker.upper(),
        "condition": condition,
        "target_price": target_price,
        "is_triggered": False
    }).execute()

async def get_alerts(user_id: str):
    return supabase.table("price_alerts").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()

async def delete_alert(user_id: str, alert_id: str):
    return supabase.table("price_alerts").delete().eq("id", alert_id).eq("user_id", user_id).execute()
