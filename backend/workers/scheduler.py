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
        
        # Schedule FXRateService poller every 5 minutes
        from services.fx_service import fx_rate_service
        self.scheduler.add_job(
            self.safe_job(fx_rate_service.fetch_latest_rates),
            'interval',
            minutes=5,
            id='poll_fx_rates',
            replace_existing=True
        )
        
        # Trigger an initial FX fetch immediately on server boot
        asyncio.create_task(fx_rate_service.fetch_latest_rates())

        # Schedule Offline Analytics Worker every 1 hour
        self.scheduler.add_job(
            self.safe_job(self.run_scheduled_analytics),
            'interval',
            hours=1,
            id='run_analytics_worker',
            replace_existing=True
        )

        # Schedule Daily Corporate Actions Ingestion daily at 4:00 AM IST
        self.scheduler.add_job(
            self.safe_job(self.run_scheduled_corporate_actions),
            'cron',
            hour=4,
            minute=0,
            timezone='Asia/Kolkata',
            id='run_corporate_actions',
            replace_existing=True
        )

        # Schedule Daily Database Checkpoint & Vacuum at 4:00 AM IST
        from infrastructure.db_maintenance import run_db_vacuum
        self.scheduler.add_job(
            self.safe_job(run_db_vacuum),
            'cron',
            hour=4,
            minute=0,
            timezone='Asia/Kolkata',
            id='db_maintenance_vacuum',
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
            hour=15, 
            minute=30, 
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
                        
                        # 1. Fetch available margin
                        cash_balance = None
                        try:
                            funds_url = "https://api.upstox.com/v2/user/get-funds-and-margin"
                            funds_res = requests.get(funds_url, headers=headers, timeout=10)
                            if funds_res.status_code == 200:
                                funds_data = funds_res.json().get("data") or {}
                                cash_balance = float(funds_data.get("equity", {}).get("available_margin") or 0.0)
                        except Exception as funds_err:
                            logger.error(f"Failed to fetch Upstox funds in scheduler: {funds_err}")
                            
                        # 2. Fetch holdings
                        url = "https://api.upstox.com/v2/portfolio/long-term-holdings"
                        response = requests.get(url, headers=headers, timeout=10)
                        
                        if response.status_code == 401 or (response.status_code == 400 and "UDAPI100050" in response.text):
                            logger.warning(f"Upstox token expired or invalid for user {user_id}. Attempting automated token refresh...")
                            try:
                                try:
                                    from scripts.auto_login_upstox import auto_login
                                except ImportError:
                                    try:
                                        from backend.scripts.auto_login_upstox import auto_login
                                    except ImportError:
                                        import sys
                                        import os
                                        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                        from scripts.auto_login_upstox import auto_login
                                
                                loop = asyncio.get_event_loop()
                                success = await loop.run_in_executor(None, auto_login)
                                if success:
                                    profile_res = supabase.table("profiles").select("broker_oauth").eq("id", user_id).execute()
                                    if profile_res.data:
                                        oauth = profile_res.data[0].get("broker_oauth") or {}
                                        access_token = oauth.get("access_token")
                                        if access_token:
                                            logger.info("Successfully refreshed Upstox token. Retrying sync...")
                                            headers = {
                                                "Authorization": f"Bearer {access_token}",
                                                "Accept": "application/json"
                                            }
                                            # Retry fetching funds and holdings
                                            try:
                                                funds_res = requests.get(funds_url, headers=headers, timeout=10)
                                                if funds_res.status_code == 200:
                                                    funds_data = funds_res.json().get("data") or {}
                                                    cash_balance = float(funds_data.get("equity", {}).get("available_margin") or 0.0)
                                            except Exception as retry_funds_err:
                                                logger.error(f"Failed to fetch Upstox funds on retry: {retry_funds_err}")
                                            
                                            response = requests.get(url, headers=headers, timeout=10)
                            except Exception as refresh_err:
                                logger.error(f"Failed to auto refresh token in scheduler: {refresh_err}")

                        if response.status_code == 200:
                            from datetime import datetime, timezone
                            data = response.json()
                            upstox_holdings = data.get("data") or []
                            
                            for h in upstox_holdings:
                                ticker = f"{h.get('tradingsymbol')}.NS"
                                shares = float(h.get("quantity") or 0.0)
                                avg_cost = float(h.get("average_price") or 0.0)
                                
                                exch = h.get("exchange") or h.get("exchange_segment") or ""
                                inst_type = h.get("instrument_type") or ""
                                no_live_price = False
                                
                                close_price = float(h.get("close_price") or 0.0)
                                last_price = float(h.get("last_price") or avg_cost)
                                
                                if inst_type == "GB" or exch == "NSE_GS" or "GS" in h.get("tradingsymbol", "") or "GB" in h.get("tradingsymbol", ""):
                                    instrument_key = h.get("instrument_token") or f"NSE_EQ|{h.get('isin')}"
                                    try:
                                        quote_url = "https://api.upstox.com/v2/market-quote/quotes"
                                        quote_res = requests.get(
                                            quote_url,
                                            headers=headers,
                                            params={"instrument_key": instrument_key},
                                            timeout=10
                                        )
                                        if quote_res.status_code == 200:
                                            quote_dict = quote_res.json().get("data", {})
                                            quote_data = next(iter(quote_dict.values())) if quote_dict else None
                                            if quote_data:
                                                last_price = float(quote_data.get("last_price") or quote_data.get("last_traded_price") or last_price)
                                                close_price = float(quote_data.get("close") or quote_data.get("ohlc", {}).get("close") or close_price or last_price)
                                            else:
                                                last_price = avg_cost
                                                no_live_price = True
                                        else:
                                            last_price = avg_cost
                                            no_live_price = True
                                    except Exception as quote_err:
                                        logger.error(f"Failed to fetch Upstox quote in scheduler for {instrument_key}: {quote_err}")
                                        last_price = avg_cost
                                        no_live_price = True
                                
                                current_price = last_price
                                if close_price <= 0:
                                    close_price = current_price
                                
                                # Cache the quote directly to market_cache
                                try:
                                    change_amount = current_price - close_price
                                    change_percent = (change_amount / close_price * 100.0) if close_price > 0 else 0.0
                                    supabase.table("market_cache").upsert({
                                        "symbol": ticker,
                                        "name": h.get("company_name") or ticker,
                                        "asset_type": "equity",
                                        "currency": "INR",
                                        "exchange": exch or "NSE",
                                        "sector": "Government Securities" if (inst_type == "GB" or exch == "NSE_GS") else ("Banking/Financial Services" if "BANK" in ticker else "Technology" if "TCS" in ticker or "INFY" in ticker else "Energy/Conglomerate"),
                                        "country": "IN",
                                        "market_cap": None,
                                        "previous_close": close_price,
                                        "last_price": current_price,
                                        "change_amount": change_amount,
                                        "change_percent": change_percent,
                                        "volume": None,
                                        "source": "upstox_quote" if (inst_type == "GB" or exch == "NSE_GS") else "upstox_sync",
                                        "fetched_at": datetime.now(tz=timezone.utc).isoformat(),
                                        "raw": h
                                    }).execute()
                                except Exception as cache_err:
                                    logger.error(f"Failed to cache Upstox price in scheduler for {ticker}: {cache_err}")
                                
                                holdings.append({
                                    "ticker": ticker,
                                    "name": h.get("company_name") or ticker,
                                    "asset_type": "equity",
                                    "sector": "Government Securities" if (inst_type == "GB" or exch == "NSE_GS") else ("Banking/Financial Services" if "BANK" in ticker else "Technology" if "TCS" in ticker or "INFY" in ticker else "Energy/Conglomerate"),
                                    "market_cap_type": "large",
                                    "shares": shares,
                                    "avg_cost": avg_cost,
                                    "current_price": current_price,
                                    "total_invested": shares * avg_cost,
                                    "current_value": shares * current_price,
                                    "pnl": shares * (current_price - avg_cost),
                                    "pnl_pct": ((current_price - avg_cost) / avg_cost * 100.0) if avg_cost > 0 else 0.0,
                                    "expense_ratio": 0.0,
                                    "category": "",
                                    "no_live_price": no_live_price
                                })
                        else:
                            logger.error(f"Scheduled sync: Failed to fetch Upstox holdings for user {user_id} (HTTP {response.status_code}): {response.text}")
                            continue
                    else:
                        # Fallback / Groww and Zerodha manual sync alerts remain unmodified in cron
                        logger.info(f"Broker {broker} for user {user_id} relies on manual or statement sync. Skipping nightly API fetch.")
                        continue
                        
                    if holdings:
                        # Run the analysis engine on new holdings
                        analysis = analyze_portfolio(holdings, None)
                        analysis["cash_balance"] = cash_balance
                        
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
                    
            logger.info("Completed scheduled daily broker sync.")
        except Exception as e:
            logger.error(f"Global cron broker sync job failed: {e}")
            
    async def run_scheduled_analytics(self):
        logger.info("Running scheduled portfolio metrics analysis worker...")
        from database.connection import AsyncSessionLocal
        from services.analytics_worker import analytics_worker_service
        from sqlalchemy.future import select
        from models.user_data import UserPortfolio
        async with AsyncSessionLocal() as session:
            try:
                stmt = select(UserPortfolio.id)
                res = await session.execute(stmt)
                portfolio_ids = res.scalars().all()
                for p_id in portfolio_ids:
                    await analytics_worker_service.calculate_and_cache_portfolio(p_id, session)
            except Exception as err:
                logger.error(f"Scheduled analytics worker job failed: {err}")

    async def run_scheduled_corporate_actions(self):
        logger.info("Starting scheduled daily corporate actions scanner...")
        from database.connection import AsyncSessionLocal
        from services.corporate_actions import corporate_actions_service
        async with AsyncSessionLocal() as session:
            await corporate_actions_service.ingest_splits_and_dividends(session)

worker = BackgroundWorker()

