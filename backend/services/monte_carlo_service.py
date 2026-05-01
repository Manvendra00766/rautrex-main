import numpy as np
import pandas as pd
import yfinance as yf
from typing import List, Optional
import asyncio
from utils import safe_json

# Simple cache for simulation results
_MC_CACHE = {}

async def run_monte_carlo_simulation(
    tickers: List[str],
    weights: List[float],
    time_horizon: int,
    num_simulations: int,
    initial_investment: float,
    confidence_level: float = 0.95
):
    cache_key = f"{','.join(tickers)}_{time_horizon}_{num_simulations}_{initial_investment}"
    if cache_key in _MC_CACHE:
        # Check cache age - clear if older than 1 hour (simplistic)
        pass

    loop = asyncio.get_event_loop()
    res = await loop.run_in_executor(None, _compute_simulation, tickers, weights, time_horizon, num_simulations, initial_investment, confidence_level)
    
    _MC_CACHE[cache_key] = res
    return res

def _compute_simulation(tickers, weights, time_horizon, num_simulations, initial_investment, confidence_level):
    if num_simulations <= 0: num_simulations = 1000
    if time_horizon <= 0: time_horizon = 365
    if initial_investment <= 0: initial_investment = 1000.0
    
    try:
        raw_data = yf.download(tickers, period="2y", progress=False)
        if raw_data.empty:
            raise ValueError(f"No historical data found for tickers: {tickers}")
        
        if 'Close' in raw_data.columns:
            data = raw_data['Close']
        else:
            data = raw_data.xs('Close', axis=1, level=0) if isinstance(raw_data.columns, pd.MultiIndex) else raw_data
            
        if isinstance(data, pd.Series):
            data = data.to_frame()
            if len(tickers) == 1: data.columns = tickers

        if data.empty:
            raise ValueError(f"Close price data is empty for tickers: {tickers}")

    except Exception as e:
        print(f"Monte Carlo Data Error: {str(e)}")
        raise ValueError(f"Market data fetch failed: {str(e)}")

    returns = data.pct_change().dropna()
    if returns.empty:
        raise ValueError(f"Insufficient historical data to compute returns for: {tickers}")
    
    # Re-align weights with available data
    available_tickers = [t for t in tickers if t in returns.columns]
    if not available_tickers:
        raise ValueError("None of the requested tickers have valid return data.")
        
    w = []
    for t in available_tickers:
        idx = tickers.index(t)
        w.append(weights[idx] if idx < len(weights) else 1.0/len(available_tickers))
    
    w = np.array(w)
    if w.sum() > 0: w = w / w.sum()
    else: w = np.ones(len(available_tickers)) / len(available_tickers)

    if len(available_tickers) == 1:
        mu_daily = float(returns[available_tickers[0]].mean())
        sigma_daily = float(returns[available_tickers[0]].std())
    else:
        mean_returns = returns[available_tickers].mean()
        cov_matrix = returns[available_tickers].cov()
        mu_daily = float(np.sum(mean_returns * w))
        variance_daily = np.dot(w.T, np.dot(cov_matrix, w))
        sigma_daily = float(np.sqrt(variance_daily)) if variance_daily > 0 else 0.0001

    mu_ann = mu_daily * 252
    sigma_ann = sigma_daily * np.sqrt(252)

    # Realistic calibration
    mu_capped = max(min(mu_ann, 0.50), -0.50)
    sigma_capped = max(min(sigma_ann, 1.0), 0.05)
    
    mu_daily_capped = mu_capped / 252
    sigma_daily_capped = sigma_capped / np.sqrt(252)
    
    # GBM simulation
    random_shocks = np.random.normal(0, 1, (time_horizon, num_simulations))
    # Geometric Brownian Motion: dS = S * (mu*dt + sigma*dW)
    # Discrete version: S_t = S_{t-1} * exp((mu - 0.5*sigma^2)*dt + sigma*sqrt(dt)*Z)
    dt = 1.0
    drift = (mu_daily_capped - 0.5 * sigma_daily_capped**2) * dt
    diffusion = sigma_daily_capped * np.sqrt(dt) * random_shocks
    
    daily_growth = np.exp(drift + diffusion)
    price_paths = initial_investment * np.cumprod(daily_growth, axis=0)

    final_values = price_paths[-1, :]
    expected_value = np.mean(final_values)
    
    sorted_final = np.sort(final_values)
    var_index = int((1 - confidence_level) * num_simulations)
    var_index = min(max(var_index, 0), num_simulations - 1)
    var_value = initial_investment - sorted_final[var_index]
    
    prob_profit = np.mean(final_values > initial_investment) * 100
    
    p5 = np.percentile(price_paths, 5, axis=1)
    p25 = np.percentile(price_paths, 25, axis=1)
    p50 = np.percentile(price_paths, 50, axis=1)
    p75 = np.percentile(price_paths, 75, axis=1)
    p95 = np.percentile(price_paths, 95, axis=1)

    num_paths_to_sample = min(num_simulations, 100)
    sample_indices = np.random.choice(num_simulations, num_paths_to_sample, replace=False)
    sampled_paths = price_paths[:, sample_indices]

    hist, bin_edges = np.histogram(final_values, bins=50)
    histogram_data = [{"bin": float((bin_edges[i] + bin_edges[i+1])/2), "count": int(hist[i])} for i in range(len(hist))]

    res = {
        "expected_value": float(expected_value),
        "var": float(var_value),
        "prob_profit": float(prob_profit),
        "volatility": float(sigma_capped),
        "worst_case": float(np.min(final_values)),
        "best_case": float(np.max(final_values)),
        "percentiles": {
            "p5": p5.tolist(),
            "p25": p25.tolist(),
            "p50": p50.tolist(),
            "p75": p75.tolist(),
            "p95": p95.tolist(),
        },
        "sampled_paths": sampled_paths.T.tolist(),
        "histogram": histogram_data
    }
    return safe_json(res)
