from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

import math
import numpy as np
import pandas as pd

from services.portfolio_calculation_service import PortfolioCalculationService



def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def safe_div(numerator: float, denominator: float) -> float:
    try:
        num = float(numerator)
        den = float(denominator)
    except (ValueError, TypeError):
        return 0.0

    if den == 0.0:
        return 0.0
        
    if math.isnan(den) or math.isinf(den):
        print("NaN/Inf detected in denominator of safe_div")
        return 0.0
        
    if math.isnan(num) or math.isinf(num):
        print("NaN/Inf detected in numerator of safe_div")
        return 0.0
        
    return num / den


def compute_drawdowns(nav_series: pd.Series) -> pd.Series:
    if nav_series.empty:
        return pd.Series(dtype=float)
    running_max = nav_series.cummax()
    # Avoid division by zero in drawdown calculation
    return safe_series_div(nav_series, running_max) - 1.0


def safe_series_div(left: pd.Series, right: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        result = left / right
    # Replace Inf and NaN with 0.0
    return result.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def compute_equity_metrics(
    equity_curve: List[Dict[str, Any]],
    initial_cash: float = 0.0,
    positions: Optional[List[Dict[str, Any]]] = None,
    price_history: Optional[Dict[str, pd.Series]] = None,
    portfolio_value: Optional[float] = None,
) -> Dict[str, Optional[float]]:
    # FIXED: Calculate performance metrics with fallbacks, returning None for risk metrics when history is insufficient
    default_res = {
        "daily_pnl": 0.0,
        "daily_return_pct": 0.0,
        "mtd_return_pct": 0.0,
        "ytd_return_pct": 0.0,
        "volatility_daily": None,
        "volatility_annualized": None,
        "sharpe_ratio": None,
        "sortino_ratio": None,
        "max_drawdown": None,
        "var_95": None,
    }
    if not equity_curve:
        return default_res

    df = pd.DataFrame(equity_curve)
    if "snapshot_date" not in df or "nav" not in df:
        return default_res

    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    df = df.sort_values("snapshot_date").drop_duplicates("snapshot_date")
    
    latest_nav = float(df["nav"].iloc[-1])
    daily_pnl = float(df.get("daily_pnl", pd.Series([0.0])).iloc[-1])
    
    # Calculate simple performance fallback if history is insufficient (< 2 points)
    if len(df) < 2:
        perf = 0.0
        if initial_cash > 0:
            perf = ((latest_nav - initial_cash) / initial_cash) * 100
        
        return {
            "daily_pnl": daily_pnl,
            "daily_return_pct": perf,
            "mtd_return_pct": perf,
            "ytd_return_pct": perf,
            "volatility_daily": None,
            "volatility_annualized": None,
            "sharpe_ratio": None,
            "sortino_ratio": None,
            "max_drawdown": None,
            "var_95": None,
        }

    # If len(df) >= 2
    df["prev_nav"] = df["nav"].shift(1).fillna(0)
    df["start_nav"] = df["nav"] - df["daily_pnl"] - df.get("net_cash_flow", 0)
    
    df["daily_ret"] = np.where(df["start_nav"] > 1.0, df["daily_pnl"] / df["start_nav"], 0.0)
    returns = df["daily_ret"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    
    prior_nav = latest_nav - daily_pnl
    if prior_nav <= 0 and len(df) >= 2:
        prior_nav = safe_float(df["nav"].iloc[-2], 0.0)
    daily_return_pct = safe_div(daily_pnl, prior_nav) * 100 if prior_nav > 0 else 0.0

    latest_date = df["snapshot_date"].iloc[-1].date()
    month_start = latest_date.replace(day=1)
    year_start = latest_date.replace(month=1, day=1)

    def _period_start_nav(period_start: date) -> float:
        period_df = df[df["snapshot_date"].dt.date >= period_start]
        if not period_df.empty:
            return safe_float(period_df["nav"].iloc[0], latest_nav)
        # Seed from earliest available NAV history entry if period snapshots do not yet exist.
        return safe_float(df["nav"].iloc[0], latest_nav)

    mtd_start_nav = _period_start_nav(month_start)
    ytd_start_nav = _period_start_nav(year_start)
    mtd_returns = returns[df["snapshot_date"].dt.date >= month_start]
    ytd_returns = returns[df["snapshot_date"].dt.date >= year_start]
    if mtd_returns.empty and mtd_start_nav > 0:
        mtd_twr = safe_div((latest_nav - mtd_start_nav), mtd_start_nav) * 100
    else:
        mtd_twr = (np.prod(1 + mtd_returns) - 1) * 100 if not mtd_returns.empty else 0.0
    if ytd_returns.empty and ytd_start_nav > 0:
        ytd_twr = safe_div((latest_nav - ytd_start_nav), ytd_start_nav) * 100
    else:
        ytd_twr = (np.prod(1 + ytd_returns) - 1) * 100 if not ytd_returns.empty else 0.0

    volatility_daily = float(returns.std()) if len(returns) >= 2 else 0.0
    volatility_annualized = volatility_daily * np.sqrt(252)

    sharpe_ratio = PortfolioCalculationService.calculate_sharpe_ratio(returns)
    sortino_ratio = PortfolioCalculationService.calculate_sortino_ratio(returns)
    max_drawdown = PortfolioCalculationService.calculate_max_drawdown(df["nav"])
    # Parametric VaR(95%): VaR% = -z * daily_volatility, where z=1.645.
    # Daily volatility is weighted sum of per-position 30-day daily return std devs.
    z_score_95 = 1.645
    inferred_portfolio_value = safe_float(portfolio_value, latest_nav)
    weighted_daily_vol = 0.0
    effective_positions = positions or []

    if effective_positions and inferred_portfolio_value > 0:
        for position in effective_positions:
            market_value = safe_float(position.get("market_value"), 0.0)
            weight = safe_div(market_value, inferred_portfolio_value)
            if weight <= 0:
                continue

            ticker = str(position.get("ticker") or "").upper()
            series = (price_history or {}).get(ticker)
            pos_sigma = None
            if series is not None:
                try:
                    pos_returns = pd.Series(series).dropna().pct_change().dropna()
                    pos_returns = pos_returns.tail(30)
                    if len(pos_returns) >= 2:
                        pos_sigma = float(pos_returns.std())
                except Exception:
                    pos_sigma = None
            if pos_sigma is None or not np.isfinite(pos_sigma) or pos_sigma <= 0:
                pos_sigma = 0.02

            weighted_daily_vol += weight * pos_sigma
    else:
        weighted_daily_vol = float(volatility_daily) if volatility_daily and volatility_daily > 0 else (0.02 if inferred_portfolio_value > 0 else 0.0)

    var_95 = -z_score_95 * weighted_daily_vol if weighted_daily_vol > 0 else 0.0

    return {
        "daily_pnl": daily_pnl,
        "daily_return_pct": daily_return_pct,
        "mtd_return_pct": mtd_twr,
        "ytd_return_pct": ytd_twr,
        "volatility_daily": volatility_daily,
        "volatility_annualized": volatility_annualized,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "max_drawdown": max_drawdown,
        "var_95": var_95,
    }


def summarize_allocation(positions: Iterable[Dict[str, Any]], total_holdings_value: float) -> Dict[str, List[Dict[str, Any]]]:
    by_sector: Dict[str, float] = defaultdict(float)
    by_asset_type: Dict[str, float] = defaultdict(float)
    by_country: Dict[str, float] = defaultdict(float)

    for position in positions:
        market_value = safe_float(position.get("market_value"))
        if market_value <= 0:
            continue
        by_sector[position.get("sector") or "Other"] += market_value
        by_asset_type[position.get("asset_type") or "equity"] += market_value
        by_country[position.get("country") or "Other"] += market_value

    def _to_rows(mapping: Dict[str, float]) -> List[Dict[str, Any]]:
        rows = []
        for label, value in sorted(mapping.items(), key=lambda item: item[1], reverse=True):
            rows.append(
                {
                    "label": label,
                    "value": value,
                    "weight_pct": safe_div(value, total_holdings_value) * 100 if total_holdings_value else 0.0,
                }
            )
        return rows

    return {
        "by_sector": _to_rows(by_sector),
        "by_asset_type": _to_rows(by_asset_type),
        "by_country": _to_rows(by_country),
    }


def build_warnings(positions: Iterable[Dict[str, Any]], cash_balance: float, total_nav: float) -> List[Dict[str, str]]:
    warnings: List[Dict[str, str]] = []
    if total_nav <= 0:
        warnings.append(
            {
                "level": "warning",
                "code": "NAV_ZERO",
                "message": "Portfolio NAV is zero or negative. Check cash flows and position data.",
            }
        )
        return warnings

    if cash_balance < (0.05 * total_nav):
        warnings.append(
            {
                "level": "warning",
                "code": "LOW_CASH",
                "message": "Cash balance is below 5% of NAV.",
            }
        )

    for position in positions:
        weight_pct = safe_float(position.get("weight_pct"))
        if weight_pct > 40:
            warnings.append(
                {
                    "level": "warning",
                    "code": "CONCENTRATION",
                    "message": f"{position.get('ticker')} exceeds 40% of portfolio weight.",
                }
            )
    return warnings
