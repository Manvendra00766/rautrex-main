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


def _synthesize_transactions(user_id: str, portfolio_id: str, position_rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    synthetic: List[Dict[str, Any]] = []
    for row in position_rows:
        shares = safe_float(row.get("shares"))
        avg_cost = safe_float(row.get("avg_cost_price"))
        if shares <= 0:
            continue
        added_at = row.get("added_at") or row.get("created_at") or _utcnow().isoformat()
        synthetic.append(
            {
                "id": f"synthetic-{row.get('id')}",
                "user_id": user_id,
                "portfolio_id": portfolio_id,
                "symbol": normalize_symbol(row.get("ticker") or ""),
                "asset_type": "equity",
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


async def load_transactions_for_portfolio(user_id: str, portfolio_id: str) -> List[Dict[str, Any]]:
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
    synthetic = _synthesize_transactions(user_id, portfolio_id, position_rows)
    return [_coerce_transaction(tx) for tx in synthetic]


def compute_portfolio_state(
    transactions: List[Dict[str, Any]],
    price_map: Dict[str, PriceSnapshot],
) -> Dict[str, Any]:
    open_lots: Dict[str, List[TaxLot]] = defaultdict(list)
    realized_pnl_by_symbol: Dict[str, float] = defaultdict(float)
    cash_balance = 0.0

    total_buys_cost = 0.0
    total_deposits = 0.0

    for raw_tx in sorted(transactions, key=_transaction_sort_key):
        tx = _coerce_transaction(raw_tx)
        tx_type = tx["transaction_type"]
        symbol = tx.get("symbol")
        quantity = safe_float(tx.get("quantity"))
        price = safe_float(tx.get("price"))
        fees = safe_float(tx.get("fees"))

        if tx_type == "DEPOSIT":
            amount = _transaction_amount(tx)
            cash_balance += amount
            total_deposits += amount
            continue
        if tx_type == "WITHDRAWAL":
            cash_balance -= _transaction_amount(tx)
            continue
        if tx_type == "DIVIDEND":
            cash_balance += _transaction_amount(tx)
            continue
        if tx_type == "FEE":
            cash_balance -= (_transaction_amount(tx) or fees)
            continue

        if tx_type == "SPLIT":
            ratio = safe_float(tx.get("split_ratio") or tx.get("metadata", {}).get("split_ratio"), 1.0)
            if ratio <= 0 or not symbol:
                continue
            for lot in open_lots[symbol]:
                lot.quantity *= ratio
                lot.cost_per_share = safe_div(lot.cost_per_share, ratio) if ratio else lot.cost_per_share
            continue

        if not symbol or quantity <= 0:
            continue

        if tx_type == "BUY":
            total_cost = (quantity * price) + fees
            total_buys_cost += total_cost
            cost_per_share = safe_div(total_cost, quantity) if quantity else 0.0
            cash_balance -= total_cost
            open_lots[symbol].append(
                TaxLot(symbol=symbol, quantity=quantity, cost_per_share=cost_per_share, opened_at=tx["executed_at"])
            )
            continue

        if tx_type == "SELL":
            if not open_lots[symbol]:
                continue

            remaining = quantity
            realized_cost = 0.0
            lot_method = tx.get("lot_method") or "FIFO"
            lot_method = lot_method.upper()

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

            proceeds = (quantity * price) - fees
            cash_balance += proceeds
            realized_pnl_by_symbol[symbol] += proceeds - realized_cost

    # Safeguard: If cash is negative because of missing deposit history, 
    # we assume an initial synthetic deposit to cover the difference.
    if cash_balance < 0:
        cash_balance = 0.0 

    positions: List[Dict[str, Any]] = []
    for symbol, lots in open_lots.items():
        shares = sum(lot.quantity for lot in lots)
        if shares <= 1e-9:
            continue
        cost_basis = sum(lot.cost_basis for lot in lots)
        avg_cost = safe_div(cost_basis, shares)
        quote = price_map.get(symbol)
        live_price = quote.last_price if quote else avg_cost
        previous_close = quote.previous_close if quote and quote.previous_close else live_price
        market_value = shares * live_price
        unrealized_pnl = market_value - cost_basis
        daily_pnl = shares * (live_price - previous_close)

        positions.append(
            {
                "ticker": symbol,
                "name": quote.name if quote else symbol,
                "asset_type": quote.asset_type if quote else "equity",
                "currency": quote.currency if quote else "USD",
                "exchange": quote.exchange if quote else None,
                "sector": quote.sector if quote else None,
                "country": quote.country if quote else None,
                "shares": shares,
                "avg_cost_per_share": avg_cost,
                "live_price": live_price,
                "previous_close": previous_close,
                "cost_basis": cost_basis,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "realized_pnl": realized_pnl_by_symbol.get(symbol, 0.0),
                "daily_pnl": daily_pnl,
                "total_return_pct": safe_div(unrealized_pnl, cost_basis) * 100 if cost_basis else 0.0,
                "change_percent": safe_div(live_price - previous_close, previous_close) * 100 if previous_close else 0.0,
            }
        )

    total_market_value = sum(position["market_value"] for position in positions)
    total_nav = cash_balance + total_market_value

    for position in positions:
        position["weight_pct"] = safe_div(position["market_value"], total_nav) * 100 if total_nav else 0.0
        position["daily_return_pct"] = safe_div(position["daily_pnl"], position["market_value"] - position["daily_pnl"]) * 100 if (position["market_value"] - position["daily_pnl"]) else 0.0

    positions.sort(key=lambda row: row["market_value"], reverse=True)

    return {
        "cash_balance": cash_balance,
        "buying_power": cash_balance,
        "total_market_value": total_market_value,
        "total_nav": total_nav,
        "positions": positions,
        "total_realized_pnl": sum(realized_pnl_by_symbol.values()),
    }


def build_equity_curve(
    transactions: List[Dict[str, Any]],
    price_history: Dict[str, pd.Series],
    end_date: date,
) -> List[Dict[str, Any]]:
    if not transactions:
        return []

    normalized_transactions = [_coerce_transaction(tx) for tx in transactions]
    start_date = min(tx["executed_at"].date() for tx in normalized_transactions)
    all_dates = pd.date_range(start=start_date, end=end_date, freq="D")
    cash_balance = 0.0
    shares_by_symbol: Dict[str, float] = defaultdict(float)
    tx_by_day: Dict[date, List[Dict[str, Any]]] = defaultdict(list)

    for tx in normalized_transactions:
        tx_by_day[tx["executed_at"].date()].append(tx)

    price_frames: Dict[str, pd.Series] = {}
    for symbol, series in price_history.items():
        normalized = series.copy()
        normalized.index = pd.to_datetime(normalized.index).normalize()
        normalized = normalized[~normalized.index.duplicated(keep="last")]
        normalized = normalized.reindex(all_dates).ffill()
        price_frames[symbol] = normalized

    curve: List[Dict[str, Any]] = []
    prev_nav = None

    for timestamp in all_dates:
        current_day = timestamp.date()
        for tx in sorted(tx_by_day.get(current_day, []), key=_transaction_sort_key):
            tx_type = tx["transaction_type"]
            symbol = tx.get("symbol")
            quantity = safe_float(tx.get("quantity"))
            price = safe_float(tx.get("price"))
            fees = safe_float(tx.get("fees"))

            if tx_type == "DEPOSIT":
                cash_balance += _transaction_amount(tx)
            elif tx_type == "WITHDRAWAL":
                cash_balance -= _transaction_amount(tx)
            elif tx_type == "DIVIDEND":
                cash_balance += _transaction_amount(tx)
            elif tx_type == "FEE":
                cash_balance -= (_transaction_amount(tx) or fees)
            elif tx_type == "BUY" and symbol:
                shares_by_symbol[symbol] += quantity
                cash_balance -= (quantity * price) + fees
            elif tx_type == "SELL" and symbol:
                shares_by_symbol[symbol] -= quantity
                cash_balance += (quantity * price) - fees
            elif tx_type == "SPLIT" and symbol:
                ratio = safe_float(tx.get("split_ratio") or tx.get("metadata", {}).get("split_ratio"), 1.0)
                if ratio > 0:
                    shares_by_symbol[symbol] *= ratio

        market_value = 0.0
        for symbol, shares in shares_by_symbol.items():
            if shares <= 0:
                continue
            series = price_frames.get(symbol)
            if series is None or series.empty:
                continue
            price = safe_float(series.loc[timestamp])
            market_value += shares * price

        nav = cash_balance + market_value
        daily_pnl = 0.0 if prev_nav is None else nav - prev_nav
        curve.append(
            {
                "snapshot_date": current_day.isoformat(),
                "nav": nav,
                "cash_balance": cash_balance,
                "market_value": market_value,
                "daily_pnl": daily_pnl,
            }
        )
        prev_nav = nav

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
                "exchange": position.get("exchange"),
                "shares": position["shares"],
                "avg_cost_price": position["avg_cost_per_share"],
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
    transactions = await load_transactions_for_portfolio(user_id, portfolio_id)
    symbols = [tx["symbol"] for tx in transactions if tx.get("symbol")]
    price_map = await get_batch_price_snapshots(symbols) if symbols else {}
    state = compute_portfolio_state(transactions, price_map)

    history_end = _utcnow().date()
    history_start = min((tx["executed_at"].date() for tx in transactions), default=history_end)
    price_history = await get_price_history(symbols, history_start, history_end) if symbols else {}
    equity_curve = build_equity_curve(transactions, price_history, history_end)
    await persist_historical_equity(user_id, portfolio_id, equity_curve)
    await sync_portfolio_positions_snapshot(portfolio_id, state["positions"])

    summary_metrics = compute_equity_metrics(equity_curve)
    beta = await compute_beta_vs_benchmark(equity_curve, portfolio.get("benchmark_symbol") or "SPY")
    exposure = compute_exposure_metrics(state["positions"], state["total_nav"])
    concentration = compute_concentration_metrics(state["positions"])

    summary = {
        "nav": state["total_nav"],
        "cash": state["cash_balance"],
        "buying_power": state["buying_power"],
        "holdings_market_value": state["total_market_value"],
        "holdings_count": len(state["positions"]),
        "daily_pnl": summary_metrics["daily_pnl"],
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
        "realized_pnl": state["total_realized_pnl"],
        "realized_pnl_total": state["total_realized_pnl"],
        "unrealized_pnl": sum(position["unrealized_pnl"] for position in state["positions"]),
    }

    allocation = summarize_allocation(state["positions"], state["total_nav"])
    warnings = build_warnings(state["positions"], state["cash_balance"], state["total_nav"])

    return {
        "portfolio": {
            "id": portfolio["id"],
            "name": portfolio["name"],
            "description": portfolio.get("description"),
            "base_currency": portfolio.get("base_currency") or "USD",
            "benchmark_symbol": portfolio.get("benchmark_symbol") or "SPY",
            "is_default": portfolio.get("is_default", False),
        },
        "summary": summary,
        "positions": state["positions"],
        "equity_curve": equity_curve,
        "allocation": allocation,
        "warnings": warnings,
        "transactions_count": len(transactions),
        "last_priced_at": max((snapshot.fetched_at.isoformat() for snapshot in price_map.values()), default=None),
    }


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
) -> Dict[str, Any]:
    payload = {
        "user_id": user_id,
        "portfolio_id": portfolio_id,
        "symbol": normalize_symbol(symbol) if symbol else None,
        "transaction_type": transaction_type.upper(),
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
        return data[0] if data else payload
    except Exception:
        transaction_type = transaction_type.upper()
        if transaction_type not in {"BUY", "SELL"} or not symbol or quantity is None or price is None:
            raise

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
                old_shares = safe_float(row.get("shares"))
                old_avg = safe_float(row.get("avg_cost_price"))
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
                        "exchange": (metadata or {}).get("exchange"),
                        "shares": quantity,
                        "avg_cost_price": price,
                    }
                ).execute()
            payload["fallback_mode"] = "portfolio_positions"
            return payload

        if not row:
            raise ValueError(f"No existing position found for {symbol}")

        old_shares = safe_float(row.get("shares"))
        if quantity > old_shares:
            raise ValueError(f"Cannot sell {quantity} shares of {symbol}; only {old_shares} available")

        new_shares = old_shares - quantity
        if new_shares <= 0:
            supabase.table("portfolio_positions").delete().eq("id", row["id"]).execute()
        else:
            supabase.table("portfolio_positions").update({"shares": new_shares}).eq("id", row["id"]).execute()
        payload["fallback_mode"] = "portfolio_positions"
        return payload
