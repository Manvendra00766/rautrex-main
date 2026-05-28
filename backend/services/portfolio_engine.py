from __future__ import annotations

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from services.analytics_engine import build_warnings, compute_equity_metrics, safe_div, safe_float, summarize_allocation
from services.pricing_engine import PriceSnapshot, get_batch_price_snapshots, get_price_history, normalize_symbol
from services.risk_engine import compute_beta_vs_benchmark, compute_concentration_metrics, compute_exposure_metrics
from services.portfolio_calculation_service import PortfolioCalculationService
from supabase_client import supabase


UTC = timezone.utc


@dataclass
class TaxLot:
    symbol: str
    quantity: float
    cost_per_share: float
    opened_at: datetime

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.cost_per_share


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time(), tzinfo=UTC)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except Exception:
            pass
    return _utcnow()


def _transaction_amount(tx: Dict[str, Any]) -> float:
    if tx.get("gross_amount") is not None:
        return abs(safe_float(tx.get("gross_amount")))
    if tx.get("amount") is not None:
        return abs(safe_float(tx.get("amount")))
    if tx.get("metadata") and isinstance(tx["metadata"], dict) and tx["metadata"].get("amount") is not None:
        return abs(safe_float(tx["metadata"]["amount"]))
    quantity = safe_float(tx.get("quantity"))
    price = safe_float(tx.get("price"))
    return abs(quantity * price)


def _transaction_sort_key(tx: Dict[str, Any]) -> Tuple[datetime, datetime]:
    return (_parse_datetime(tx.get("executed_at")), _parse_datetime(tx.get("created_at")))


def _coerce_transaction(tx: Dict[str, Any]) -> Dict[str, Any]:
    tx = dict(tx)
    tx["transaction_type"] = str(tx.get("transaction_type") or "BUY").upper()
    tx["symbol"] = normalize_symbol(tx.get("symbol") or tx.get("ticker") or "")
    tx["quantity"] = safe_float(tx.get("quantity"))
    tx["price"] = safe_float(tx.get("price"))
    tx["fees"] = safe_float(tx.get("fees"))
    tx["gross_amount"] = safe_float(tx.get("gross_amount"))
    tx["lot_method"] = str(tx.get("lot_method") or "FIFO").upper()
    tx["metadata"] = tx.get("metadata") or {}
    tx["executed_at"] = _parse_datetime(tx.get("executed_at"))
    tx["created_at"] = _parse_datetime(tx.get("created_at"))
    return tx


def _synthesize_transactions(
    user_id: str,
    portfolio_id: str,
    position_rows: Iterable[Dict[str, Any]],
    portfolio_created_at: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    synthetic: List[Dict[str, Any]] = []
    
    # Calculate target synthetic execution time:
    # If portfolio_created_at is provided, use it.
    # Otherwise, default to 30 days ago.
    if portfolio_created_at:
        target_date = portfolio_created_at
    else:
        target_date = _utcnow() - timedelta(days=30)
    
    target_date_str = target_date.isoformat()

    for row in position_rows:
        shares = safe_float(row.get("quantity") or row.get("shares"))
        avg_cost = safe_float(row.get("avg_cost") or row.get("avg_cost_price"))
        if shares <= 0:
            continue
            
        added_at = row.get("added_at") or row.get("created_at") or target_date_str
        try:
            added_at_dt = _parse_datetime(added_at)
            # If the position has a creation date newer than our target date, backdate it to target_date
            if added_at_dt > target_date:
                added_at = target_date_str
        except Exception:
            added_at = target_date_str

        synthetic.append(
            {
                "id": f"synthetic-{row.get('id')}",
                "user_id": user_id,
                "portfolio_id": portfolio_id,
                "symbol": normalize_symbol(row.get("ticker") or ""),
                "asset_type": row.get("asset_type") or "equity",
                "transaction_type": "BUY",
                "quantity": shares,
                "price": avg_cost,
                "gross_amount": shares * avg_cost,
                "fees": 0.0,
                "lot_method": "FIFO",
                "executed_at": added_at,
                "created_at": added_at,
                "metadata": {"synthetic_from_position": True, "exchange": row.get("exchange")},
            }
        )
    return synthetic


async def list_user_portfolios(user_id: str) -> List[Dict[str, Any]]:
    try:
        response = (
            supabase.table("portfolios")
            .select("*")
            .eq("user_id", user_id)
            .is_("deleted_at", "null")
            .order("is_default", desc=True)
            .order("created_at", desc=False)
            .execute()
        )
        return response.data or []
    except Exception:
        response = (
            supabase.table("portfolios")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .execute()
        )
        return response.data or []


async def get_portfolio_record(user_id: str, portfolio_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    portfolios = await list_user_portfolios(user_id)
    if not portfolios:
        return None
    if portfolio_id:
        for portfolio in portfolios:
            if str(portfolio["id"]) == str(portfolio_id):
                return portfolio
    for portfolio in portfolios:
        if portfolio.get("is_default"):
            return portfolio
    return portfolios[0]


async def load_transactions_for_portfolio(user_id: str, portfolio_id: str, portfolio_created_at: Optional[datetime] = None) -> List[Dict[str, Any]]:
    transactions: List[Dict[str, Any]] = []
    try:
        response = (
            supabase.table("transactions")
            .select("*")
            .eq("user_id", user_id)
            .eq("portfolio_id", portfolio_id)
            .order("executed_at", desc=False)
            .order("created_at", desc=False)
            .execute()
        )
        raw_txs = response.data or []
        # Deduplication check (symbol, type, qty, price, time)
        seen = set()
        for r in raw_txs:
            fingerprint = (r.get("symbol"), r.get("transaction_type"), r.get("quantity"), r.get("price"), r.get("executed_at"))
            if fingerprint not in seen:
                transactions.append(r)
                seen.add(fingerprint)
    except Exception:
        transactions = []

    if transactions:
        return [_coerce_transaction(tx) for tx in transactions]

    try:
        fallback = (
            supabase.table("portfolio_positions")
            .select("*")
            .eq("portfolio_id", portfolio_id)
            .is_("deleted_at", "null")
            .execute()
        )
    except Exception:
        fallback = (
            supabase.table("portfolio_positions")
            .select("*")
            .eq("portfolio_id", portfolio_id)
            .execute()
        )
    position_rows = fallback.data or []
    synthetic = _synthesize_transactions(user_id, portfolio_id, position_rows, portfolio_created_at)
    return [_coerce_transaction(tx) for tx in synthetic]


def compute_portfolio_state(
    transactions: List[Dict[str, Any]],
    price_map: Dict[str, PriceSnapshot],
    initial_cash: float = 0.0,
) -> Dict[str, Any]:
    # FIXED: Calculate cash balance using initial_cash and trace all transactions, skipping initial_deposit to avoid double-counting
    open_lots: Dict[str, List[TaxLot]] = defaultdict(list)
    realized_pnl_by_symbol: Dict[str, float] = defaultdict(float)
    cash_balance = initial_cash

    for raw_tx in sorted(transactions, key=_transaction_sort_key):
        tx = _coerce_transaction(raw_tx)
        tx_type = tx["transaction_type"]
        symbol = tx.get("symbol")
        quantity = safe_float(tx.get("quantity"))
        price = safe_float(tx.get("price"))
        fees = safe_float(tx.get("fees"))
        gross_amount = _transaction_amount(tx)

        if tx_type == "DEPOSIT":
            if tx.get("metadata", {}).get("source") == "initial_deposit":
                continue
            cash_balance += gross_amount
        elif tx_type == "WITHDRAWAL":
            cash_balance -= gross_amount
        elif tx_type == "DIVIDEND":
            cash_balance += gross_amount
        elif tx_type == "FEE":
            cash_balance -= (gross_amount or fees)
        elif tx_type == "BUY" and symbol:
            total_cost = (quantity * price) + fees
            if not tx.get("metadata", {}).get("synthetic_from_position"):
                cash_balance -= total_cost
            cost_per_share = safe_div(total_cost, quantity)
            open_lots[symbol].append(
                TaxLot(symbol=symbol, quantity=quantity, cost_per_share=cost_per_share, opened_at=tx["executed_at"])
            )
        elif tx_type == "SELL" and symbol:
            if not open_lots[symbol]:
                continue
            
            proceeds = (quantity * price) - fees
            cash_balance += proceeds
            
            remaining = quantity
            realized_cost = 0.0
            lot_method = tx.get("lot_method") or "FIFO"
            
            while remaining > 1e-9 and open_lots[symbol]:
                lot = open_lots[symbol][0] if lot_method == "FIFO" else open_lots[symbol][-1]
                matched = min(remaining, lot.quantity)
                realized_cost += matched * lot.cost_per_share
                lot.quantity -= matched
                remaining -= matched
                if lot.quantity <= 1e-9:
                    if lot_method == "FIFO":
                        open_lots[symbol].pop(0)
                    else:
                        open_lots[symbol].pop()
            
            realized_pnl_by_symbol[symbol] += proceeds - realized_cost
        elif tx_type == "SPLIT" and symbol:
            ratio = safe_float(tx.get("split_ratio") or tx.get("metadata", {}).get("split_ratio"), 1.0)
            if ratio > 0:
                for lot in open_lots[symbol]:
                    lot.quantity *= ratio
                    lot.cost_per_share = safe_div(lot.cost_per_share, ratio)

    # Calculate positions
    positions: List[Dict[str, Any]] = []
    total_market_value = 0.0
    total_daily_pnl = 0.0

    for symbol, lots in open_lots.items():
        shares = sum(lot.quantity for lot in lots)
        if shares <= 1e-9:
            continue
            
        cost_basis = sum(lot.cost_basis for lot in lots)
        avg_cost = safe_div(cost_basis, shares)
        quote = price_map.get(symbol)
        
        live_price = quote.last_price if quote else avg_cost
        prev_close = quote.previous_close if quote and quote.previous_close else live_price
        
        market_value = shares * live_price
        unrealized_pnl = market_value - cost_basis
        daily_pnl = shares * (live_price - prev_close)
        
        total_market_value += market_value
        total_daily_pnl += daily_pnl

        positions.append({
            "ticker": symbol,
            "name": quote.name if quote else symbol,
            "asset_type": quote.asset_type if quote else "equity",
            "sector": quote.sector if quote else "Unknown",
            "country": quote.country if quote else "Unknown",
            "shares": shares,
            "avg_cost_per_share": avg_cost,
            "live_price": live_price,
            "previous_close": prev_close,
            "cost_basis": cost_basis,
            "market_value": market_value,
            "unrealized_pnl": unrealized_pnl,
            "realized_pnl": realized_pnl_by_symbol.get(symbol, 0.0),
            "daily_pnl": daily_pnl,
            "total_return_pct": safe_div(unrealized_pnl, cost_basis) * 100 if cost_basis else 0.0,
            "change_percent": safe_div(live_price - prev_close, prev_close) * 100 if prev_close else 0.0,
        })

    total_nav = PortfolioCalculationService.calculate_nav(cash_balance, positions)
    positions = PortfolioCalculationService.calculate_weights(positions)
    total_daily_pnl = PortfolioCalculationService.calculate_daily_pnl(positions)

    positions.sort(key=lambda x: x["market_value"], reverse=True)

    return {
        "cash_balance": cash_balance,
        "total_market_value": total_market_value,
        "total_nav": total_nav,
        "total_daily_pnl": total_daily_pnl,
        "positions": positions,
        "total_realized_pnl": sum(realized_pnl_by_symbol.values()),
    }


def build_equity_curve(
    transactions: List[Dict[str, Any]],
    price_history: Dict[str, pd.Series],
    end_date: date,
    initial_cash: float = 0.0,
    portfolio_created_at: Optional[date] = None,
) -> List[Dict[str, Any]]:
    # FIXED: Build equity curve with baseline if portfolio was created today to guarantee 2-point flat line
    if not transactions:
        start = (portfolio_created_at or end_date) - timedelta(days=1)
        return [
            {
                "snapshot_date": start.isoformat(),
                "nav": initial_cash,
                "cash_balance": initial_cash,
                "market_value": 0.0,
                "daily_pnl": 0.0,
                "net_cash_flow": initial_cash,
            },
            {
                "snapshot_date": end_date.isoformat(),
                "nav": initial_cash,
                "cash_balance": initial_cash,
                "market_value": 0.0,
                "daily_pnl": 0.0,
                "net_cash_flow": 0.0,
            }
        ]

    normalized_transactions = [_coerce_transaction(tx) for tx in transactions]
    start_date = min(tx["executed_at"].date() for tx in normalized_transactions)
    if portfolio_created_at:
        start_date = min(start_date, portfolio_created_at)
        
    if start_date == end_date:
        start_date = start_date - timedelta(days=1)

    all_dates = pd.date_range(start=start_date, end=end_date, freq="D")
    cash_balance = initial_cash
    shares_by_symbol: Dict[str, float] = defaultdict(float)
    tx_by_day: Dict[date, List[Dict[str, Any]]] = defaultdict(list)

    for tx in normalized_transactions:
        if tx.get("metadata", {}).get("source") == "initial_deposit":
            continue
        tx_by_day[tx["executed_at"].date()].append(tx)

    price_frames: Dict[str, pd.Series] = {}
    from utils import normalize_history
    for symbol, series in price_history.items():
        if series.empty:
            continue
        try:
            # Flatten multi-index if present
            if isinstance(series.index, pd.MultiIndex):
                if 'Date' in series.index.names:
                    series = series.xs(symbol, level=1) if symbol in series.index.get_level_values(1) else series
            
            # The series index might contain tuples or unparseable items
            # Convert series to list of tuples and use our normalizer
            raw_history = list(zip(series.index, series.values))
            clean_list = normalize_history(raw_history)
            
            if not clean_list:
                continue
                
            clean_df = pd.DataFrame(clean_list)
            clean_df['date'] = pd.to_datetime(clean_df['date'])
            clean_series = clean_df.set_index('date')['nav']
            
            clean_series = clean_series[~clean_series.index.duplicated(keep="last")]
            clean_series = clean_series.reindex(all_dates.tz_localize(None)).ffill()
            price_frames[symbol] = clean_series
        except Exception as e:
            print(f"Error normalizing history for {symbol}: {e}")
            continue

    curve: List[Dict[str, Any]] = []
    prev_nav = 0.0
    prev_shares: Dict[str, float] = defaultdict(float)

    for timestamp in all_dates:
        current_day = timestamp.date()
        daily_net_cash_flow = 0.0
        
        # Process transactions for the day
        for tx in sorted(tx_by_day.get(current_day, []), key=_transaction_sort_key):
            tx_type = tx["transaction_type"]
            symbol = tx.get("symbol")
            quantity = safe_float(tx.get("quantity"))
            price = safe_float(tx.get("price"))
            fees = safe_float(tx.get("fees"))
            gross_amount = _transaction_amount(tx)

            if tx_type == "DEPOSIT":
                cash_balance += gross_amount
                daily_net_cash_flow += gross_amount
            elif tx_type == "WITHDRAWAL":
                cash_balance -= gross_amount
                daily_net_cash_flow -= gross_amount
            elif tx_type == "DIVIDEND":
                cash_balance += gross_amount
                daily_net_cash_flow += gross_amount
            elif tx_type == "FEE":
                cash_balance -= (gross_amount or fees)
                daily_net_cash_flow -= (gross_amount or fees)
            elif tx_type == "BUY" and symbol:
                total_cost = (quantity * price) + fees
                shares_by_symbol[symbol] += quantity
                if not tx.get("metadata", {}).get("synthetic_from_position"):
                    cash_balance -= total_cost
                # BUY itself is not a cash flow out of the portfolio system, 
                # but it changes cash balance. Net cash flow into the system is 0.
            elif tx_type == "SELL" and symbol:
                proceeds = (quantity * price) - fees
                shares_by_symbol[symbol] -= quantity
                cash_balance += proceeds
                # SELL itself is not a cash flow out of the portfolio system.
            elif tx_type == "SPLIT" and symbol:
                ratio = safe_float(tx.get("split_ratio") or tx.get("metadata", {}).get("split_ratio"), 1.0)
                if ratio > 0:
                    shares_by_symbol[symbol] *= ratio

        # Calculate market value using prices for THIS day
        market_value = 0.0
        price_pnl = 0.0
        
        for symbol, shares in shares_by_symbol.items():
            if shares <= 0 and prev_shares.get(symbol, 0.0) <= 0:
                continue
                
            series = price_frames.get(symbol)
            if series is None or series.empty:
                continue
            
            # Current price
            try:
                current_price = safe_float(series.loc[timestamp])
            except KeyError:
                # Reindex/ffill should have handled this, but be safe
                current_price = 0.0
            
            if shares > 0:
                market_value += shares * current_price
            
            # Calculate price-driven P&L: (P_t - P_{t-1}) * Shares_{t-1}
            # Note: We use shares at start of day (prev_shares) for price change P&L
            if symbol in prev_shares and prev_shares[symbol] > 0:
                try:
                    prev_timestamp = timestamp - timedelta(days=1)
                    prev_price = safe_float(series.loc[prev_timestamp])
                    price_pnl += prev_shares[symbol] * (current_price - prev_price)
                except KeyError:
                    pass

        nav = cash_balance + market_value
        # For the very first day, daily_pnl is usually 0 unless we have price history before start
        daily_pnl = price_pnl
        
        curve.append(
            {
                "snapshot_date": current_day.isoformat(),
                "nav": nav,
                "cash_balance": cash_balance,
                "market_value": market_value,
                "daily_pnl": daily_pnl,
                "net_cash_flow": daily_net_cash_flow,
            }
        )
        prev_nav = nav
        prev_shares = shares_by_symbol.copy()

    return curve


async def persist_historical_equity(user_id: str, portfolio_id: str, equity_curve: List[Dict[str, Any]]) -> None:
    if not equity_curve:
        return
    payload = []
    for row in equity_curve[-370:]:
        payload.append(
            {
                "user_id": user_id,
                "portfolio_id": portfolio_id,
                "snapshot_date": row["snapshot_date"],
                "nav": row["nav"],
                "cash_balance": row["cash_balance"],
                "market_value": row["market_value"],
                "daily_pnl": row["daily_pnl"],
                "gross_exposure": row["market_value"],
                "net_exposure": row["market_value"],
            }
        )
    try:
        supabase.table("historical_equity").upsert(payload).execute()
    except Exception:
        return


async def sync_portfolio_positions_snapshot(portfolio_id: str, positions: List[Dict[str, Any]]) -> None:
    try:
        supabase.table("portfolio_positions").delete().eq("portfolio_id", portfolio_id).execute()
        if not positions:
            return
        payload = [
            {
                "portfolio_id": portfolio_id,
                "ticker": position["ticker"],
                "shares": position["shares"],
                "avg_cost_price": position["avg_cost_per_share"],
                "exchange": "NSE" if position["ticker"].endswith(".NS") or position["ticker"].endswith(".BO") else "NASDAQ"
            }
            for position in positions
        ]
        supabase.table("portfolio_positions").insert(payload).execute()
    except Exception:
        return


async def get_portfolio_overview(user_id: str, portfolio_id: Optional[str] = None) -> Dict[str, Any]:
    portfolio = await get_portfolio_record(user_id, portfolio_id)
    if not portfolio:
        return {
            "portfolio": None,
            "summary": None,
            "positions": [],
            "equity_curve": [],
            "allocation": {"by_sector": [], "by_asset_type": [], "by_country": []},
            "warnings": [],
        }

    portfolio_id = str(portfolio["id"])
    
    portfolio_created_dt = None
    if portfolio.get("created_at"):
        try:
            portfolio_created_dt = _parse_datetime(portfolio["created_at"])
        except Exception:
            pass

    transactions = await load_transactions_for_portfolio(user_id, portfolio_id, portfolio_created_dt)
    symbols = [tx["symbol"] for tx in transactions if tx.get("symbol")]
    price_map = await get_batch_price_snapshots(symbols) if symbols else {}
    initial_cash = safe_float(portfolio.get("initial_cash", 0.0))
    state = compute_portfolio_state(transactions, price_map, initial_cash)

    history_end = _utcnow().date()
    history_start = min((tx["executed_at"].date() for tx in transactions), default=history_end)
    price_history = await get_price_history(symbols, history_start, history_end) if symbols else {}
    
    # Enrich positions with risk metrics
    import numpy as np
    for pos in state["positions"]:
        symbol = pos["ticker"]
        quote = price_map.get(symbol)
        
        # 1. market_cap
        mcap = quote.market_cap if (quote and quote.market_cap is not None) else None
        pos["market_cap"] = mcap
        
        # 2. beta
        beta = 1.0
        if quote and quote.raw and quote.raw.get("beta") is not None:
            try:
                beta = float(quote.raw["beta"])
            except Exception:
                pass
        pos["beta"] = beta
        
        # 3. volatility
        pos_sigma = None
        series = price_history.get(symbol)
        if series is not None and not series.empty:
            try:
                if isinstance(series.index, pd.MultiIndex):
                    if 'Date' in series.index.names:
                        series = series.xs(symbol, level=1) if symbol in series.index.get_level_values(1) else series
                
                # Use clean normalizer to match equity curve calculation
                from utils import normalize_history
                raw_history = list(zip(series.index, series.values))
                clean_list = normalize_history(raw_history)
                if clean_list:
                    clean_df = pd.DataFrame(clean_list)
                    clean_series = clean_df.set_index(pd.to_datetime(clean_df['date']))['nav']
                    pos_series = clean_series.dropna().pct_change().dropna()
                    if len(pos_series) >= 2:
                        pos_sigma = float(pos_series.std())
            except Exception:
                pass
        if pos_sigma is None or not np.isfinite(pos_sigma) or pos_sigma <= 0:
            pos_sigma = 0.02 # 2% daily volatility fallback
        
        vol = pos_sigma * np.sqrt(252) * 100
        pos["volatility"] = vol
        
        # 4. var_95
        pos["var_95"] = 1.645 * pos_sigma * pos["market_value"]
        
        # 5. risk_contribution
        weight_pct = pos.get("weight_pct", 0.0)
        pos["risk_contribution"] = (weight_pct / 100.0) * beta

    portfolio_created_at = None
    if portfolio_created_dt:
        portfolio_created_at = portfolio_created_dt.date()
        
    equity_curve = build_equity_curve(
        transactions, 
        price_history, 
        history_end, 
        initial_cash=initial_cash,
        portfolio_created_at=portfolio_created_at
    )
    await persist_historical_equity(user_id, portfolio_id, equity_curve)
    await sync_portfolio_positions_snapshot(portfolio_id, state["positions"])

    summary_metrics = compute_equity_metrics(
        equity_curve,
        initial_cash,
        positions=state["positions"],
        price_history=price_history,
        portfolio_value=state["total_nav"],
    )
    
    beta_err = None
    try:
        beta = await compute_beta_vs_benchmark(equity_curve, portfolio.get("benchmark_symbol") or "SPY")
    except Exception as e:
        print(f"Error calculating beta for portfolio {portfolio_id}: {e}")
        beta = None
        beta_err = f"Beta calculation failed: {str(e)}"

    exposure = compute_exposure_metrics(state["positions"], state["total_nav"])
    concentration = compute_concentration_metrics(state["positions"])

    summary = {
        "nav": state["total_nav"],
        "cash": state["cash_balance"],
        "buying_power": state["cash_balance"],
        "holdings_market_value": state["total_market_value"],
        "holdings_count": len(state["positions"]),
        "daily_pnl": state["total_daily_pnl"],
        "daily_return_pct": summary_metrics["daily_return_pct"],
        "mtd_return_pct": summary_metrics["mtd_return_pct"],
        "ytd_return_pct": summary_metrics["ytd_return_pct"],
        "gross_exposure": exposure["gross_exposure"],
        "gross_exposure_pct": exposure["gross_exposure_pct"],
        "net_exposure": exposure["net_exposure"],
        "net_exposure_pct": exposure["net_exposure_pct"],
        "volatility_annualized": summary_metrics["volatility_annualized"],
        "sharpe_ratio": summary_metrics["sharpe_ratio"],
        "sortino_ratio": summary_metrics["sortino_ratio"],
        "max_drawdown": summary_metrics["max_drawdown"],
        "var_95": summary_metrics["var_95"],
        "beta_vs_spy": beta,
        "top_position_pct": concentration["top_position_pct"],
        "herfindahl_index": concentration["herfindahl_index"],
        "realized_pnl_total": state["total_realized_pnl"],
        "unrealized_pnl": sum(position["unrealized_pnl"] for position in state["positions"]),
        "unrealized_pnl_total": sum(position["unrealized_pnl"] for position in state["positions"]),
    }

    allocation = summarize_allocation(state["positions"], state["total_market_value"])
    warnings = build_warnings(state["positions"], state["cash_balance"], state["total_nav"])
    if beta_err:
        warnings.append(beta_err)

    # FIXED: Return flat API contract root fields alongside legacy nested keys for Phase 3 compliance
    
    # Calculate detailed system alerts (Bug 7)
    alerts = []
    # Concentration risk (> 70% weight)
    for pos in state["positions"]:
        weight = pos.get("weight_pct", 0.0)
        if weight > 70.0:
            alerts.append({
                "id": f"conc_{pos['ticker']}",
                "type": "risk_breach",
                "severity": "warning",
                "title": f"Concentration Risk — {pos['ticker']}",
                "message": f"{pos['ticker']} represents {weight:.1f}% of portfolio. Recommended max: 70%.",
                "affected_asset": pos["ticker"],
                "triggered_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "threshold": 70.0,
                "current_value": weight
            })
    # Negative cash balance warning
    if state["cash_balance"] < 0.0:
        p_currency = portfolio.get("currency") or portfolio.get("base_currency") or "USD"
        curr_symbol = "₹" if p_currency == "INR" else "$"
        alerts.append({
            "id": "neg_cash",
            "type": "risk_breach",
            "severity": "critical",
            "title": "Negative Cash Balance",
            "message": f"Portfolio cash balance is {curr_symbol}{state['cash_balance']:,.2f}. Check transaction records.",
            "affected_asset": None,
            "triggered_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "threshold": 0.0,
            "current_value": state["cash_balance"]
        })

    # Prepare sector allocation list of dicts for Phase 3 API Contract
    SECTOR_COLORS = {
        "Information Technology": "#3B82F6",
        "Consumer Discretionary": "#F59E0B",
        "Financials": "#10B981",
        "Healthcare": "#EF4444",
        "Energy": "#8B5CF6",
        "Industrials": "#6B7280",
        "Communication Services": "#EC4899",
        "Consumer Staples": "#14B8A6",
        "Materials": "#F97316",
        "Real Estate": "#84CC16",
        "Utilities": "#06B6D4",
        "Other": "#9CA3AF",
    }
    
    sector_allocation = []
    for item in allocation.get("by_sector", []):
        sector_name = item.get("label", "Other")
        sector_allocation.append({
            "sector": sector_name,
            "value": round(item.get("value", 0.0), 2),
            "weight": round(item.get("weight_pct", 0.0), 2),
            "color": SECTOR_COLORS.get(sector_name, SECTOR_COLORS["Other"])
        })

    # Prepare flat list of nav_history
    nav_history = []
    for row in equity_curve:
        nav_history.append({
            "date": row["snapshot_date"],
            "nav": round(row["nav"], 2)
        })

    last_updated_time = max((snapshot.fetched_at.isoformat().replace("+00:00", "Z") for snapshot in price_map.values()), default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))

    # Construct the final nested + flat dictionary
    res_dict = {
        # Flat fields (Phase 3 API Contract)
        "portfolio_id": portfolio_id,
        "name": portfolio["name"],
        "initial_cash": initial_cash,
        "cash_balance": round(state["cash_balance"], 2),
        "market_value": round(state["total_market_value"], 2),
        "nav": round(state["total_nav"], 2),
        "gross_exposure": round(exposure["gross_exposure"], 2),
        "unrealized_pnl": round(sum(pos["unrealized_pnl"] for pos in state["positions"]), 2),
        "realized_pnl": round(state["total_realized_pnl"], 2),
        "daily_pnl": round(state["total_daily_pnl"], 2),
        "daily_pnl_pct": round(summary_metrics["daily_return_pct"], 2) if summary_metrics["daily_return_pct"] is not None else 0.0,
        "performance_this_month_pct": round(summary_metrics["mtd_return_pct"], 2) if summary_metrics["mtd_return_pct"] is not None else 0.0,
        "performance_ytd_pct": round(summary_metrics["ytd_return_pct"], 2) if summary_metrics["ytd_return_pct"] is not None else 0.0,
        "max_drawdown_pct": round(summary_metrics["max_drawdown"], 2) if summary_metrics["max_drawdown"] is not None else 0.0,
        "sharpe_ratio": round(summary_metrics["sharpe_ratio"], 2) if summary_metrics["sharpe_ratio"] is not None else 0.0,
        "max_daily_loss_95var": round((summary_metrics["var_95"] or 0.0) * state["total_nav"], 2) if summary_metrics["var_95"] is not None else 0.0,
        "holdings_count": len(state["positions"]),
        "positions": state["positions"],
        "sector_allocation": sector_allocation,
        "nav_history": nav_history,
        "alerts": alerts,
        "last_updated": last_updated_time,

        # Legacy nested fields (for backwards-compatibility)
        "portfolio": {
            "id": portfolio["id"],
            "name": portfolio["name"],
            "description": portfolio.get("description"),
            "currency": portfolio.get("base_currency") or "USD",
            "base_currency": portfolio.get("base_currency") or "USD",
            "benchmark_symbol": portfolio.get("benchmark_symbol") or "SPY",
            "is_default": portfolio.get("is_default", False),
            "margin_enabled": portfolio.get("margin_enabled", False),
            "broker": "upstox" if "upstox" in (portfolio.get("name") or "").lower() or "upstox" in (portfolio.get("description") or "").lower() else ("zerodha" if "zerodha" in (portfolio.get("name") or "").lower() else ("groww" if "groww" in (portfolio.get("name") or "").lower() else "broker")),
        },
        "summary": summary,
        "equity_curve": equity_curve,
        "allocation": allocation,
        "warnings": warnings,
        "transactions_count": len(transactions),
        "last_priced_at": max((snapshot.fetched_at.isoformat() for snapshot in price_map.values()), default=None),
    }

    # Serialize transactions to prevent datetime JSON errors
    serialized_transactions = []
    for tx in transactions:
        tx_copy = dict(tx)
        if isinstance(tx_copy.get("executed_at"), datetime):
            tx_copy["executed_at"] = tx_copy["executed_at"].isoformat()
        if isinstance(tx_copy.get("created_at"), datetime):
            tx_copy["created_at"] = tx_copy["created_at"].isoformat()
        serialized_transactions.append(tx_copy)

    res_dict["transactions"] = serialized_transactions

    return res_dict


async def create_transaction(
    user_id: str,
    portfolio_id: str,
    transaction_type: str,
    *,
    symbol: Optional[str] = None,
    quantity: Optional[float] = None,
    price: Optional[float] = None,
    gross_amount: Optional[float] = None,
    fees: float = 0.0,
    executed_at: Optional[str] = None,
    lot_method: str = "FIFO",
    metadata: Optional[Dict[str, Any]] = None,
    external_id: Optional[str] = None,
    skip_cash_check: bool = False,
    ) -> Dict[str, Any]:
    transaction_type = transaction_type.upper()

    # Pre-validation for margin mode
    if transaction_type == "BUY" and quantity and price and not skip_cash_check:

        portfolio = await get_portfolio_record(user_id, portfolio_id)
        margin_enabled = portfolio.get("margin_enabled", False) if portfolio else False
        
        if not margin_enabled:
            # We need current cash balance. Load all transactions and compute state.
            txs = await load_transactions_for_portfolio(user_id, portfolio_id)
            # Use a dummy price map as we only care about cash
            initial_cash = safe_float(portfolio.get("initial_cash", 0.0)) if portfolio else 0.0
            current_state = compute_portfolio_state(txs, {}, initial_cash)
            current_cash = current_state["cash_balance"]
            
            total_cost = (quantity * price) + fees
            if total_cost > current_cash:
                raise ValueError(f"Insufficient cash for BUY transaction. Required: {total_cost}, Available: {current_cash}. Margin mode is disabled.")

    payload = {
        "user_id": user_id,
        "portfolio_id": portfolio_id,
        "symbol": normalize_symbol(symbol) if symbol else None,
        "transaction_type": transaction_type,
        "quantity": quantity,
        "price": price,
        "gross_amount": gross_amount,
        "fees": fees,
        "executed_at": executed_at or _utcnow().isoformat(),
        "lot_method": lot_method.upper(),
        "metadata": metadata or {},
        "external_id": external_id,
    }
    
    try:
        response = supabase.table("transactions").insert(payload).execute()
        data = response.data or []
        if data:
             payload = data[0]
    except Exception as e:
        print(f"Transaction log failed: {e}. Falling back to position update.")
        
    try:
        if transaction_type not in {"BUY", "SELL"} or not symbol or quantity is None or price is None:
            return payload
        # ... rest of the function ...

        symbol = normalize_symbol(symbol)
        existing = (
            supabase.table("portfolio_positions")
            .select("*")
            .eq("portfolio_id", portfolio_id)
            .eq("ticker", symbol)
            .limit(1)
            .execute()
        )
        row = (existing.data or [None])[0]

        if transaction_type == "BUY":
            if row:
                old_shares = safe_float(row.get("shares") or row.get("quantity"))
                old_avg = safe_float(row.get("avg_cost_price") or row.get("avg_cost"))
                new_shares = old_shares + quantity
                new_avg = safe_div((old_shares * old_avg) + (quantity * price) + fees, new_shares)
                supabase.table("portfolio_positions").update(
                    {"shares": new_shares, "avg_cost_price": new_avg}
                ).eq("id", row["id"]).execute()
            else:
                supabase.table("portfolio_positions").insert(
                    {
                        "portfolio_id": portfolio_id,
                        "ticker": symbol,
                        "shares": quantity,
                        "avg_cost_price": price,
                        "exchange": "NASDAQ" # Default for audit/missing
                    }
                ).execute()
            payload["fallback_mode"] = "portfolio_positions"
            return payload

        if not row:
             return payload # Can't sell what you don't have

        old_shares = safe_float(row.get("shares") or row.get("quantity"))
        if quantity > old_shares:
             quantity = old_shares # Sell all if trying to sell more than available

        new_shares = old_shares - quantity
        if new_shares <= 0:
            supabase.table("portfolio_positions").delete().eq("id", row["id"]).execute()
        else:
            supabase.table("portfolio_positions").update({"shares": new_shares}).eq("id", row["id"]).execute()
        payload["fallback_mode"] = "portfolio_positions"
        return payload
    except Exception as e:
        print(f"Position sync failed during transaction: {e}")
        return payload
