from apscheduler.schedulers.asyncio import AsyncIOScheduler
from core.logger import logger
from services.streaming_engine import streaming_engine
from services.alert_monitor import check_price_alerts
import asyncio

class BackgroundWorker:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        # Start streaming engine loop
        asyncio.create_task(streaming_engine.start())
        
        # Schedule price alert checker every 1 minute
        self.scheduler.add_job(
            self.safe_job(check_price_alerts), 
            'interval', 
            minutes=1, 
            id='check_alerts', 
            replace_existing=True
        )
        
        # Add a job to cleanup stale websocket channels or caches
        self.scheduler.add_job(
            self.safe_job(self.cleanup_task), 
            'interval', 
            hours=1, 
            id='cleanup_task', 
            replace_existing=True
        )

        self.scheduler.add_job(
            self.safe_job(self.sync_all_broker_portfolios), 
            'cron', 
            hour=18, 
            minute=0, 
            timezone='Asia/Kolkata',
            id='sync_broker_portfolios', 
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Background workers started.")

    def stop(self):
        asyncio.create_task(streaming_engine.stop())
        self.scheduler.shutdown()
        logger.info("Background workers stopped.")

    def safe_job(self, func):
        """Wrapper to catch and log exceptions in background jobs."""
        async def wrapper(*args, **kwargs):
            try:
                if asyncio.iscoroutinefunction(func):
                    await func(*args, **kwargs)
                else:
                    func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Background job {func.__name__} failed: {e}")
        return wrapper

    async def cleanup_task(self):
        logger.info("Running background cleanup tasks...")
        # Implementation for clearing old cache keys, old notifications, etc.

    async def sync_all_broker_portfolios(self):
        """
        Background job to sync holdings for all users who have active broker connections.
        Runs daily at 6 PM IST after Indian stock markets close.
        """
        logger.info("Starting scheduled daily broker portfolio synchronization...")
        try:
            from supabase_client import supabase
            from services import db_service
            from services.portfolio_analyzer import analyze_portfolio
            import requests
            
            # Fetch all user profiles with stored broker credentials
            res = supabase.table("profiles").select("id, broker_oauth").execute()
            if not res.data:
                logger.info("No active broker profiles found to synchronize.")
                return
                
            active_count = 0
            for profile in res.data:
                user_id = profile.get("id")
                oauth = profile.get("broker_oauth") or {}
                
                if not oauth or "broker" not in oauth:
                    continue
                    
                broker = oauth.get("broker").lower()
                access_token = oauth.get("access_token")
                
                if not access_token:
                    continue
                    
                active_count += 1
                logger.info(f"Syncing {broker} holdings for user {user_id}...")
                
                try:
                    holdings = []
                    cash_balance = 0.0
                    
                    if broker == "upstox":
                        # Fetch live holdings from Upstox API
                        headers = {
                            "Authorization": f"Bearer {access_token}",
                            "Accept": "application/json"
                        }
                        # Production URL for holdings
                        url = "https://api.upstox.com/v2/portfolio/long-term-holdings"
                        response = requests.get(url, headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            data = response.json()
                            upstox_holdings = data.get("data") or []
                            
                            for h in upstox_holdings:
                                ticker = f"{h.get('tradingsymbol')}.NS"
                                shares = float(h.get("quantity") or 0.0)
                                avg_cost = float(h.get("average_price") or 0.0)
                                current_price = float(h.get("last_price") or avg_cost)
                                
                                holdings.append({
                                    "ticker": ticker,
                                    "name": h.get("company_name") or ticker,
                                    "asset_type": "equity",
                                    "sector": "Banking/Financial Services" if "BANK" in ticker else "Technology" if "TCS" in ticker or "INFY" in ticker else "Energy/Conglomerate",
                                    "market_cap_type": "large",
                                    "shares": shares,
                                    "avg_cost": avg_cost,
                                    "current_price": current_price,
                                    "total_invested": shares * avg_cost,
                                    "current_value": shares * current_price,
                                    "pnl": shares * (current_price - avg_cost),
                                    "pnl_pct": ((current_price - avg_cost) / avg_cost * 100.0) if avg_cost > 0 else 0.0,
                                    "expense_ratio": 0.0,
                                    "category": ""
                                })
                        elif response.status_code == 401:
                            logger.warning(f"Upstox token expired for user {user_id}. Attempting token refresh...")
                            # Code to refresh token using client credentials
                            refresh_token = oauth.get("refresh_token")
                            if refresh_token:
                                client_id = os.getenv("UPSTOX_CLIENT_ID")
                                client_secret = os.getenv("UPSTOX_CLIENT_SECRET")
                                refresh_url = "https://api.upstox.com/v2/oauth/token"
                                refresh_res = requests.post(refresh_url, data={
                                    "grant_type": "refresh_token",
                                    "refresh_token": refresh_token,
                                    "client_id": client_id,
                                    "client_secret": client_secret
                                }, timeout=10)
                                
                                if refresh_res.status_code == 200:
                                    new_oauth = refresh_res.json()
                                    new_oauth["broker"] = "upstox"
                                    # Update profiles table
                                    supabase.table("profiles").update({"broker_oauth": new_oauth}).eq("id", user_id).execute()
                                    logger.info(f"Successfully refreshed Upstox token for user {user_id}.")
                            continue
                    else:
                        # Fallback / Groww and Zerodha manual sync alerts remain unmodified in cron
                        logger.info(f"Broker {broker} for user {user_id} relies on manual or statement sync. Skipping nightly API fetch.")
                        continue
                        
                    if holdings:
                        # Run the analysis engine on new holdings
                        analysis = analyze_portfolio(holdings, None)
                        
                        # Save the updated telemetry to profile preferences and portfolios table
                        await db_service.save_imported_portfolio(
                            user_id=user_id,
                            broker=broker,
                            holdings=holdings,
                            analysis=analysis
                        )
                        logger.info(f"Successfully sync-refreshed holdings for user {user_id}. Total Value: INR {analysis['current_value']}")
                        
                except Exception as user_err:
                    logger.error(f"Failed to sync broker data for user {user_id}: {user_err}")
                    
            logger.info(f"Completed scheduled daily broker sync. Processed {active_count} profiles.")
            
        except Exception as e:
            logger.error(f"Global cron broker sync job failed: {e}")

worker = BackgroundWorker()

