from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from services.analytics_engine import safe_div
from services.pricing_engine import get_price_history


async def compute_beta_vs_benchmark(
    equity_curve: List[Dict[str, Any]],
    benchmark_symbol: str = "SPY",
) -> float:
    if len(equity_curve) < 3:
        return 0.0

    df = pd.DataFrame(equity_curve)
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"])
    df = df.sort_values("snapshot_date")
    nav_returns = df["nav"].astype(float).pct_change().dropna()
    if nav_returns.empty:
        return 0.0

    start_date = df["snapshot_date"].iloc[0].date()
    end_date = df["snapshot_date"].iloc[-1].date()
    benchmark_history = await get_price_history([benchmark_symbol], start_date, end_date)
    benchmark_series = benchmark_history.get(benchmark_symbol)
    if benchmark_series is None or benchmark_series.empty:
        return 0.0

    if isinstance(benchmark_series, pd.DataFrame):
        # If it's a DataFrame, try to get 'Close' column or use first column
        if "Close" in benchmark_series.columns:
            benchmark_df = benchmark_series[["Close"]].copy()
            benchmark_df.columns = ["close"]
        else:
            benchmark_df = benchmark_series.iloc[:, [0]].copy()
            benchmark_df.columns = ["close"]
    else:
        benchmark_df = benchmark_series.to_frame(name="close")
        
    benchmark_df.index = pd.to_datetime(benchmark_df.index).normalize()
    benchmark_returns = benchmark_df["close"].pct_change().dropna()

    nav_df = nav_returns.to_frame(name="portfolio")
    nav_df.index = pd.to_datetime(df["snapshot_date"].iloc[1:]).dt.normalize()
    merged = nav_df.join(benchmark_returns.to_frame(name="benchmark"), how="inner").dropna()
    if len(merged) < 3:
        return 0.0

    benchmark_var = float(np.var(merged["benchmark"]))
    if benchmark_var <= 0:
        return 0.0

    covariance = np.cov(merged["portfolio"], merged["benchmark"])[0, 1]
    return float(covariance / benchmark_var)


def compute_concentration_metrics(positions: List[Dict[str, Any]]) -> Dict[str, float]:
    weights = [max(float(position.get("weight_pct", 0.0)) / 100.0, 0.0) for position in positions]
    if not weights:
        return {"top_position_pct": 0.0, "herfindahl_index": 0.0}
    return {
        "top_position_pct": max(weights) * 100,
        "herfindahl_index": float(sum(weight * weight for weight in weights)),
    }


def compute_exposure_metrics(positions: List[Dict[str, Any]], total_nav: float) -> Dict[str, float]:
    gross = sum(abs(float(position.get("market_value", 0.0))) for position in positions)
    net = sum(float(position.get("market_value", 0.0)) for position in positions)
    return {
        "gross_exposure": gross,
        "gross_exposure_pct": safe_div(gross, total_nav) * 100 if total_nav else 0.0,
        "net_exposure": net,
        "net_exposure_pct": safe_div(net, total_nav) * 100 if total_nav else 0.0,
    }
