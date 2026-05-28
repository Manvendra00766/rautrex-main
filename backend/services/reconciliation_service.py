import requests
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from core.logger import logger
from supabase_client import supabase
from services.pricing_engine import upsert_cached_price, PriceSnapshot

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
    
    try:
        # A. Fetch Cash Margin
        funds_url = "https://api.upstox.com/v2/user/fund-margin"
        loop = asyncio.get_event_loop()
        funds_res = await loop.run_in_executor(None, lambda: requests.get(funds_url, headers=headers, timeout=10))
        if funds_res.status_code == 200:
            funds_data = funds_res.json().get("data") or {}
            upstox_cash = float(funds_data.get("equity", {}).get("available_margin") or 0.0)
        else:
            report["log_messages"].append(f"Failed to fetch fresh cash from Upstox (HTTP {funds_res.status_code})")
            
        # B. Fetch Holdings
        holdings_url = "https://api.upstox.com/v2/portfolio/long-term-holdings"
        holdings_res = await loop.run_in_executor(None, lambda: requests.get(holdings_url, headers=headers, timeout=10))
        if holdings_res.status_code == 200:
            upstox_holdings_raw = holdings_res.json().get("data") or []
        else:
            logger.error(f"Reconciliation: Failed to fetch Upstox holdings: {holdings_res.text}")
            report["reason"] = f"Failed to fetch Upstox holdings (HTTP {holdings_res.status_code})"
            return report
    except Exception as e:
        logger.error(f"Reconciliation: API request failed: {e}")
        report["reason"] = f"Upstox API request failed: {str(e)}"
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
    for ticker, up_pos in upstox_map.items():
        try:
            h = up_pos["raw"]
            last_price = float(h.get("last_price") or up_pos["avg_cost"])
            close_price = float(h.get("close_price") or last_price)
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
                sector="Government Securities" if is_gsec else "Indian Equity",
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
