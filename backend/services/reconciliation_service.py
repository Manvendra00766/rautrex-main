import requests
import asyncio
import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from core.logger import logger
from supabase_client import supabase
from services.pricing_engine import upsert_cached_price, PriceSnapshot

async def _trigger_upstox_auto_login() -> bool:
    """
    Attempts to programmatically log in to Upstox using Playwright
    and updates the broker_oauth token in Supabase.
    """
    logger.info("Reconciliation: Triggering programmatically automated Upstox login refresh...")
    try:
        try:
            from scripts.auto_login_upstox import auto_login
        except ImportError:
            try:
                from backend.scripts.auto_login_upstox import auto_login
            except ImportError:
                import sys
                sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                from scripts.auto_login_upstox import auto_login

        loop = asyncio.get_event_loop()
        success = await loop.run_in_executor(None, auto_login)
        return bool(success)
    except Exception as e:
        logger.error(f"Reconciliation: Automated login exception: {e}")
        return False

async def reconcile_portfolio_with_upstox(user_id: str, portfolio_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Synchronously reconciles the user's local database portfolio with their live Upstox account.
    If any discrepancy in cash margin, position quantities, or average costs is found,
    it automatically corrects (self-heals) the database.
    
    Returns a reconciliation log/report.
    """
    report = {
        "status": "skipped",
        "reason": "",
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "healed_cash": False,
        "cash_before": 0.0,
        "cash_after": 0.0,
        "positions_added": [],
        "positions_deleted": [],
        "positions_updated": [],
        "log_messages": []
    }

    # 1. Fetch user's active Upstox token
    try:
        profile_res = supabase.table("profiles").select("broker_oauth").eq("id", user_id).execute()
        if not profile_res.data:
            report["reason"] = "Profile not found"
            return report
            
        oauth = profile_res.data[0].get("broker_oauth") or {}
        token = oauth.get("access_token")
        broker = str(oauth.get("broker") or "").lower()
        
        # If no active connection is set in profile, but we have credentials in .env,
        # we can attempt to establish it automatically on the fly.
        if broker != "upstox":
            env_user_email = os.getenv("USER_EMAIL")
            user_email_res = supabase.table("profiles").select("email").eq("id", user_id).execute()
            user_email = user_email_res.data[0].get("email") if user_email_res.data else None
            
            if user_email and env_user_email and user_email.lower() == env_user_email.lower():
                logger.info(f"Reconciliation: No active Upstox connection for {user_email}, but env configured. Triggering auto-login...")
                success = await _trigger_upstox_auto_login()
                if success:
                    profile_res = supabase.table("profiles").select("broker_oauth").eq("id", user_id).execute()
                    if profile_res.data:
                        oauth = profile_res.data[0].get("broker_oauth") or {}
                        token = oauth.get("access_token")
                        broker = str(oauth.get("broker") or "").lower()
            
        if not token or broker != "upstox":
            report["reason"] = "No active Upstox connection found"
            return report
    except Exception as e:
        logger.error(f"Reconciliation: Error fetching profile: {e}")
        report["reason"] = f"Failed to fetch profile: {str(e)}"
        return report

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # 2. Fetch fresh funds and holdings from Upstox
    upstox_cash = None
    upstox_holdings_raw = []
    
    async def fetch_upstox_data(headers_dict):
        cash = None
        holdings = []
        err_msg = None
        is_auth_error = False
        
        try:
            # Note: We intentionally do NOT fetch cash via get-funds-and-margin.
            # Upstox's "available_margin" includes collateral and unsettled trades,
            # which inaccurately overwrites the user's manual idle cash balance.
            # Cash is left as None so the reconciler preserves the user's local input.
            
            # Fetch Holdings
            holdings_url = "https://api.upstox.com/v2/portfolio/long-term-holdings"
            loop = asyncio.get_event_loop()
            holdings_res = await loop.run_in_executor(None, lambda: requests.get(holdings_url, headers=headers_dict, timeout=10))
            if holdings_res.status_code == 200:
                holdings = holdings_res.json().get("data") or []
            elif holdings_res.status_code == 401 or "UDAPI100050" in holdings_res.text:
                is_auth_error = True
                err_msg = f"Holdings fetch auth failure ({holdings_res.status_code}): {holdings_res.text}"
            else:
                err_msg = f"Failed to fetch Upstox holdings (HTTP {holdings_res.status_code})"
        except Exception as api_err:
            err_msg = f"Upstox API request failed: {str(api_err)}"
            
        return cash, holdings, err_msg, is_auth_error

    # Try 1
    upstox_cash, upstox_holdings_raw, error_message, token_expired = await fetch_upstox_data(headers)
    
    # If expired, trigger auto-refresh and Try 2!
    if token_expired:
        logger.warning(f"Reconciliation: Upstox access token expired or invalid (Details: {error_message}). Attempting automated token refresh...")
        refresh_success = await _trigger_upstox_auto_login()
        if refresh_success:
            try:
                profile_res = supabase.table("profiles").select("broker_oauth").eq("id", user_id).execute()
                if profile_res.data:
                    oauth = profile_res.data[0].get("broker_oauth") or {}
                    new_token = oauth.get("access_token")
                    if new_token:
                        logger.info("Reconciliation: Successfully fetched refreshed token. Retrying Upstox API requests...")
                        headers["Authorization"] = f"Bearer {new_token}"
                        upstox_cash, upstox_holdings_raw, error_message, token_expired = await fetch_upstox_data(headers)
            except Exception as reload_err:
                logger.error(f"Reconciliation: Failed to reload profile after refresh: {reload_err}")
                error_message = f"Failed to reload profile after refresh: {str(reload_err)}"
                
    # Check final results
    if error_message and (upstox_cash is None or not upstox_holdings_raw):
        logger.error(f"Reconciliation: {error_message}")
        report["reason"] = error_message
        if "Failed to fetch fresh cash" in error_message:
            report["log_messages"].append(error_message)
        else:
            return report

    # 3. Retrieve local portfolio and positions
    try:
        # If portfolio_id is supplied, get that one; otherwise find the default Upstox Portfolio
        if portfolio_id:
            port_res = supabase.table("portfolios").select("*").eq("id", portfolio_id).eq("user_id", user_id).execute()
        else:
            port_res = supabase.table("portfolios").select("*").eq("user_id", user_id).eq("name", "Upstox Portfolio").execute()
            
        if not port_res.data:
            # If no portfolio exists yet, skip reconciliation (onboarding will create it first)
            report["reason"] = "No matching portfolio record found to reconcile"
            return report
            
        portfolio = port_res.data[0]
        active_portfolio_id = portfolio["id"]
        local_cash = float(portfolio.get("cash_balance") or 0.0)
        
        # Get local positions
        pos_res = supabase.table("portfolio_positions").select("*").eq("portfolio_id", active_portfolio_id).execute()
        local_positions = pos_res.data or []
    except Exception as e:
        logger.error(f"Reconciliation: Error fetching local portfolio state: {e}")
        report["reason"] = f"Failed to retrieve local portfolio state: {str(e)}"
        return report

    report["status"] = "completed"
    report["cash_before"] = local_cash

    # 4. Reconcile Cash Balance (Self-Healing)
    if upstox_cash is not None and abs(upstox_cash - local_cash) > 0.01:
        try:
            supabase.table("portfolios").update({
                "cash_balance": upstox_cash,
                "initial_cash": upstox_cash
            }).eq("id", active_portfolio_id).execute()
            report["healed_cash"] = True
            report["cash_after"] = upstox_cash
            report["log_messages"].append(f"Healed cash balance: INR {local_cash:,.2f} -> INR {upstox_cash:,.2f}")
        except Exception as e:
            logger.error(f"Reconciliation: Failed to heal cash: {e}")
            report["log_messages"].append(f"Failed to heal cash balance discrepancy: {str(e)}")
    else:
        report["cash_after"] = local_cash

    # 5. Reconcile Positions (Self-Healing)
    # Parse Upstox holdings into mapping: ticker -> holding details
    upstox_map = {}
    for h in upstox_holdings_raw:
        ticker = f"{h.get('tradingsymbol')}.NS"
        shares = float(h.get("quantity") or 0.0)
        avg_cost = float(h.get("average_price") or 0.0)
        
        if shares > 0:
            upstox_map[ticker] = {
                "shares": shares,
                "avg_cost": avg_cost,
                "raw": h
            }

    # Parse Local positions mapping: ticker -> db_row
    local_map = {p["ticker"]: p for p in local_positions}

    # Identify corrections
    to_delete = []
    to_insert = []
    to_update = []

    # Check local positions that should be deleted or updated
    for ticker, local_pos in local_map.items():
        if ticker not in upstox_map:
            to_delete.append(ticker)
        else:
            up_pos = upstox_map[ticker]
            local_shares = float(local_pos["shares"] or 0.0)
            local_avg_cost = float(local_pos["avg_cost_price"] or 0.0)
            
            shares_diff = abs(up_pos["shares"] - local_shares) > 1e-5
            cost_diff = abs(up_pos["avg_cost"] - local_avg_cost) > 1e-3
            
            if shares_diff or cost_diff:
                to_update.append((ticker, up_pos["shares"], up_pos["avg_cost"]))

    # Check Upstox positions that are missing locally
    for ticker, up_pos in upstox_map.items():
        if ticker not in local_map:
            to_insert.append((ticker, up_pos["shares"], up_pos["avg_cost"]))

    # Execute healing writes
    # A. Deletions
    if to_delete:
        try:
            supabase.table("portfolio_positions").delete().eq("portfolio_id", active_portfolio_id).in_("ticker", to_delete).execute()
            report["positions_deleted"] = to_delete
            report["log_messages"].append(f"Deleted stale positions: {', '.join(to_delete)}")
        except Exception as e:
            logger.error(f"Reconciliation: Failed to delete positions {to_delete}: {e}")
            report["log_messages"].append(f"Error deleting stale positions {to_delete}: {str(e)}")

    # B. Insertions
    if to_insert:
        payload = []
        for ticker, shares, avg_cost in to_insert:
            payload.append({
                "portfolio_id": active_portfolio_id,
                "ticker": ticker,
                "exchange": "NSE",
                "shares": shares,
                "avg_cost_price": avg_cost,
                "asset_type": "Stock"
            })
        try:
            supabase.table("portfolio_positions").insert(payload).execute()
            inserted_symbols = [t[0] for t in to_insert]
            report["positions_added"] = inserted_symbols
            report["log_messages"].append(f"Added missing positions: {', '.join(inserted_symbols)}")
        except Exception as e:
            logger.error(f"Reconciliation: Failed to insert positions: {e}")
            report["log_messages"].append(f"Error adding missing positions: {str(e)}")

    # C. Updates
    for ticker, shares, avg_cost in to_update:
        try:
            supabase.table("portfolio_positions").update({
                "shares": shares,
                "avg_cost_price": avg_cost
            }).eq("portfolio_id", active_portfolio_id).eq("ticker", ticker).execute()
            
            local_pos = local_map[ticker]
            msg = f"Healed position {ticker}: {local_pos['shares']} shares @ ₹{local_pos['avg_cost_price']:,.2f} -> {shares} shares @ ₹{avg_cost:,.2f}"
            report["positions_updated"].append(ticker)
            report["log_messages"].append(msg)
        except Exception as e:
            logger.error(f"Reconciliation: Failed to update position {ticker}: {e}")
            report["log_messages"].append(f"Error updating position {ticker}: {str(e)}")

    # 6. Cache fresh quotes returned in holdings directly to market_cache
    tickers = list(upstox_map.keys())
    from services.pricing_engine import get_batch_price_snapshots, SECTOR_MAP
    price_map = {}
    if tickers:
        try:
            price_map = await get_batch_price_snapshots(tickers)
        except Exception as p_err:
            logger.error(f"Reconciliation: Failed to batch fetch prices: {p_err}")

    for ticker, up_pos in upstox_map.items():
        try:
            h = up_pos["raw"]
            quote = price_map.get(ticker)
            upstox_ltp = float(h.get("last_price") or 0.0)
            upstox_close = float(h.get("close_price") or 0.0)
            
            last_price = upstox_ltp if upstox_ltp > 0 else (quote.last_price if quote else up_pos["avg_cost"])
            close_price = upstox_close if upstox_close > 0 else (quote.previous_close if (quote and quote.previous_close) else last_price)
                
            if close_price <= 0:
                close_price = last_price
                
            change_amount = last_price - close_price
            change_percent = (change_amount / close_price * 100.0) if close_price > 0 else 0.0
            
            inst_type = h.get("instrument_type") or ""
            exch = h.get("exchange") or h.get("exchange_segment") or ""
            is_gsec = inst_type == "GB" or exch == "NSE_GS" or "GS" in ticker or "GB" in ticker
            
            snap = PriceSnapshot(
                symbol=ticker,
                name=h.get("company_name") or ticker,
                asset_type="equity",
                currency="INR",
                exchange=exch or "NSE",
                sector="Government Securities" if is_gsec else SECTOR_MAP.get(ticker, "Indian Equity"),
                country="IN",
                market_cap=None,
                previous_close=close_price,
                last_price=last_price,
                change_amount=change_amount,
                change_percent=change_percent,
                volume=None,
                source="upstox_reconciliation_sync",
                fetched_at=datetime.now(tz=timezone.utc),
                raw=h
            )
            asyncio.create_task(upsert_cached_price(snap))
        except Exception as cache_err:
            logger.error(f"Reconciliation: Failed to cache quote for {ticker}: {cache_err}")

    # Log summary
    if report["healed_cash"] or to_delete or to_insert or to_update:
        logger.info(f"Reconciliation: Portfolio {active_portfolio_id} healed successfully: {report['log_messages']}")
    else:
        logger.info(f"Reconciliation: Portfolio {active_portfolio_id} was already 100% aligned with Upstox.")

    return report
