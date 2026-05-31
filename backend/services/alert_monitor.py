import yfinance as yf
import pandas as pd
from supabase_client import supabase
from services.notification_service import create_notification
from websocket_app.manager import manager
from typing import List, Dict, Any
from core.logger import logger
from datetime import datetime

async def check_price_alerts():
    """
    APScheduler job to check price alerts and create notifications.
    """
    logger.info("Running price alert check...")
    # Fetch all untriggered alerts
    alerts_res = supabase.table("price_alerts").select("*").eq("is_triggered", False).execute()
    alerts = alerts_res.data
    
    if not alerts:
        return

    # Group alerts by ticker
    tickers = list(set([a['ticker'] for a in alerts]))
    
    try:
        from services.pricing_engine import get_batch_price_snapshots
        price_map = await get_batch_price_snapshots(tickers)
        
        current_prices = {}
        for ticker in tickers:
            snap = price_map.get(ticker)
            if snap:
                current_prices[ticker] = float(snap.last_price)

        for alert in alerts:
            ticker = alert['ticker']
            current_price = current_prices.get(ticker)
            if current_price is None:
                continue
                
            condition = alert['condition'].lower() # 'above' or 'below'
            target_price = alert['target_price']
            
            triggered = False
            if condition == 'above' and current_price >= target_price:
                triggered = True
            elif condition == 'below' and current_price <= target_price:
                triggered = True
                
            if triggered:
                logger.info(f"ALERT TRIGGERED: {ticker} {condition} {target_price} (Current: {current_price})")
                
                # 1. Update DB
                supabase.table("price_alerts").update({
                    "is_triggered": True,
                    "triggered_at": datetime.now().isoformat()
                }).eq("id", alert['id']).execute()
                
                # 2. Create Persistent Notification
                await create_notification(
                    user_id=alert['user_id'],
                    type="price_alert",
                    title=f"Price Alert: {ticker}",
                    body=f"{ticker} has moved {condition} your target of {target_price}. Current price: {round(current_price, 2)}",
                    metadata={"ticker": ticker, "target_price": target_price, "current_price": current_price}
                )

                # 3. Send Real-time WebSocket Alert
                # Broadcast to the user's private channel
                await manager.broadcast_to_channel(f"user:{alert['user_id']}", {
                    "type": "ALERT_TRIGGERED",
                    "symbol": ticker,
                    "target_price": target_price,
                    "current_price": current_price,
                    "condition": condition.upper()
                })
                
    except Exception as e:
        logger.error(f"Error in check_price_alerts: {e}")
