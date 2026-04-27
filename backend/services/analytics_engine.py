from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def safe_div(numerator: float, denominator: float) -> float:
    if denominator in (0, 0.0):
        return 0.0
    return numerator / denominator


def compute_drawdowns(nav_series: pd.Series) -> pd.Series:
    if nav_series.empty:
        return pd.Series(dtype=float)
    running_max = nav_series.cummax()
    return safe_series_div(nav_series, running_max) - 1.0


def safe_series_div(left: pd.Series, right: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        result = left / right
    return result.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def compute_equity_metrics(equity_curve: List[Dict[str, Any]]) -> Dict[str, float]:
    if not equity_curve:
        return {
            "daily_pnl": 0.0,
            "daily_return_pct": 0.0,
            "mtd_return_pct": 0.0,
            "ytd_return_pct": 0.0,
            "volatility_daily": 0.0,
            "volatility_annualized": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "var_95": 0.0,
        }

    df = pd.DataFrame(equity_curve)
    if "snapshot_date" not in df or "nav" not in df:
        return {
            "daily_pnl": 0.0,
            "daily_return_pct": 0.0,
            "mtd_return_pct": 0.0,
            "ytd_return_pct": 0.0,
            "volatility_daily": 0.0,
            "volatility_annualized": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "var_95": 0.0,
        }

    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    df = df.sort_values("snapshot_date").drop_duplicates("snapshot_date")
    nav = df["nav"].astype(float)
    returns = nav.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    drawdowns = compute_drawdowns(nav)

    latest_nav = float(nav.iloc[-1]) if not nav.empty else 0.0
    prev_nav = float(nav.iloc[-2]) if len(nav) > 1 else latest_nav
    daily_pnl = latest_nav - prev_nav
    daily_return_pct = safe_div(daily_pnl, prev_nav) * 100 if prev_nav else 0.0

    latest_date = df["snapshot_date"].iloc[-1].date()
    month_start = latest_date.replace(day=1)
    year_start = latest_date.replace(month=1, day=1)

    month_df = df[df["snapshot_date"].dt.date >= month_start]
    year_df = df[df["snapshot_date"].dt.date >= year_start]

    mtd_start_nav = float(month_df["nav"].iloc[0]) if not month_df.empty else latest_nav
    ytd_start_nav = float(year_df["nav"].iloc[0]) if not year_df.empty else latest_nav

    volatility_daily = float(returns.std()) if not returns.empty else 0.0
    volatility_annualized = volatility_daily * np.sqrt(252)

    risk_free_daily = 0.02 / 252
    excess_returns = returns - risk_free_daily
    mean_excess = float(excess_returns.mean()) if not excess_returns.empty else 0.0
    sharpe_ratio = safe_div(mean_excess * 252, volatility_annualized)

    downside = excess_returns[excess_returns < 0]
    downside_vol = float(downside.std()) * np.sqrt(252) if not downside.empty else 0.0
    sortino_ratio = safe_div(mean_excess * 252, downside_vol)

    var_95 = float(np.percentile(returns, 5)) if not returns.empty else 0.0

    return {
        "daily_pnl": daily_pnl,
        "daily_return_pct": daily_return_pct,
        "mtd_return_pct": safe_div(latest_nav - mtd_start_nav, mtd_start_nav) * 100 if mtd_start_nav else 0.0,
        "ytd_return_pct": safe_div(latest_nav - ytd_start_nav, ytd_start_nav) * 100 if ytd_start_nav else 0.0,
        "volatility_daily": volatility_daily,
        "volatility_annualized": volatility_annualized,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "max_drawdown": float(drawdowns.min()) if not drawdowns.empty else 0.0,
        "var_95": var_95,
    }


def summarize_allocation(positions: Iterable[Dict[str, Any]], total_nav: float) -> Dict[str, List[Dict[str, Any]]]:
    by_sector: Dict[str, float] = defaultdict(float)
    by_asset_type: Dict[str, float] = defaultdict(float)
    by_country: Dict[str, float] = defaultdict(float)

    for position in positions:
        market_value = safe_float(position.get("market_value"))
        if market_value <= 0:
            continue
        by_sector[position.get("sector") or "Unknown"] += market_value
        by_asset_type[position.get("asset_type") or "equity"] += market_value
        by_country[position.get("country") or "Unknown"] += market_value

    def _to_rows(mapping: Dict[str, float]) -> List[Dict[str, Any]]:
        rows = []
        for label, value in sorted(mapping.items(), key=lambda item: item[1], reverse=True):
            rows.append(
                {
                    "label": label,
                    "value": value,
                    "weight_pct": safe_div(value, total_nav) * 100 if total_nav else 0.0,
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
