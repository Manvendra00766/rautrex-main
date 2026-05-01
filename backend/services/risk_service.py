import numpy as np
import pandas as pd
import yfinance as yf
from scipy import stats
from scipy.stats import norm
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from utils import safe_json

# Helpers
def _get_returns(tickers: List[str], start: str, end: str) -> pd.DataFrame:
    try:
        data = yf.download(tickers, start=start, end=end, progress=False)
        if data.empty:
            return pd.DataFrame()
        
        # Handle the MultiIndex columns if multiple tickers
        if 'Close' in data:
            data = data['Close']
        else:
            # Fallback if yfinance structure varies
            data = data.xs('Close', axis=1, level=0) if isinstance(data.columns, pd.MultiIndex) else data
            
        if isinstance(data, pd.Series):
            data = data.to_frame()
            
        return data.pct_change().dropna()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def calculate_drawdowns(returns: pd.Series) -> pd.Series:
    if returns.empty:
        return pd.Series()
    cum_returns = (1 + returns).cumprod()
    rolling_max = cum_returns.cummax()
    drawdowns = (cum_returns / rolling_max) - 1.0
    return drawdowns

# --- RISK METRICS ---

async def calculate_portfolio_risk(
    portfolio: List[Dict[str, Any]], 
    start_date: str, 
    end_date: str, 
    benchmark: str = "^GSPC"
) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    def _calc():
        tickers = [item['ticker'] for item in portfolio]
        weights = np.array([item['weight'] for item in portfolio])
        
        # Download data
        all_tickers = list(set(tickers + [benchmark]))
        data = _get_returns(all_tickers, start_date, end_date)
        
        if data.empty or len(data) < 10:
            raise ValueError(f"Insufficient data for tickers: {all_tickers}. Check if they are valid and have history in yfinance.")
            
        # Ensure all tickers are in data
        available_tickers = [t for t in tickers if t in data.columns]
        if not available_tickers:
            raise ValueError(f"None of the portfolio tickers {tickers} were found in the downloaded data.")
        
        # Re-align weights for available tickers
        final_tickers = []
        final_weights = []
        for i, t in enumerate(tickers):
            if t in available_tickers:
                final_tickers.append(t)
                final_weights.append(weights[i])
        
        # Normalize weights if some tickers were dropped
        final_weights = np.array(final_weights)
        if final_weights.sum() > 0:
            final_weights = final_weights / final_weights.sum()
        else:
            raise ValueError("All portfolio tickers are missing data.")

        port_returns = (data[final_tickers] * final_weights).sum(axis=1)
        
        if benchmark not in data.columns:
            # Fallback benchmark if original fails
            bench_returns = port_returns * 0 + 0 # Zero returns
        else:
            bench_returns = data[benchmark]
        
        # 1. VaR (95%)
        # Historical
        var_hist_95 = np.percentile(port_returns, 5) if not port_returns.empty else 0
        var_hist_99 = np.percentile(port_returns, 1) if not port_returns.empty else 0
        
        # Parametric
        mu = port_returns.mean()
        sigma = port_returns.std()
        if pd.isna(sigma) or sigma == 0: sigma = 0.0001
        var_param_95 = norm.ppf(0.05, mu, sigma)
        
        # Monte Carlo (simple)
        sim_returns = np.random.normal(mu, sigma, 10000)
        var_mc_95 = np.percentile(sim_returns, 5)
        
        # CVaR (Expected Shortfall) 95%
        tail_returns = port_returns[port_returns <= var_hist_95]
        cvar_95 = tail_returns.mean() if not tail_returns.empty else var_hist_95
        
        # 2. Drawdowns
        drawdowns = calculate_drawdowns(port_returns)
        max_drawdown = drawdowns.min() if not drawdowns.empty else 0
        
        # Drawdown Duration
        is_underwater = drawdowns < 0
        underwater_streaks = is_underwater.groupby((~is_underwater).cumsum()).sum()
        max_dd_duration = int(underwater_streaks.max()) if not underwater_streaks.empty else 0
        
        # 3. Ratios
        risk_free = 0.065
        daily_rf = risk_free / 252
        excess_returns = port_returns - daily_rf
        
        ann_return = (1 + port_returns.mean()) ** 252 - 1 if not pd.isna(port_returns.mean()) else 0
        ann_vol = sigma * np.sqrt(252)
        
        sharpe = (ann_return - risk_free) / ann_vol if ann_vol > 0 else 0
        
        downside_returns = excess_returns[excess_returns < 0]
        downside_vol = downside_returns.std() * np.sqrt(252) if not downside_returns.empty else 0.0001
        sortino = (ann_return - risk_free) / downside_vol if downside_vol > 0 else 0
        
        calmar = ann_return / abs(max_drawdown) if max_drawdown < -0.001 else 0
        
        neg_sum = abs(excess_returns[excess_returns < 0].sum())
        omega = excess_returns[excess_returns > 0].sum() / neg_sum if neg_sum > 0 else 0
        
        # 4. Alpha & Beta
        if len(data) < 20:
            beta = 1.0
        else:
            try:
                # Need shared index for covariance
                common_data = pd.concat([port_returns, bench_returns], axis=1).dropna()
                if len(common_data) > 10:
                    cov_matrix = np.cov(common_data.iloc[:, 0], common_data.iloc[:, 1])
                    beta = cov_matrix[0, 1] / cov_matrix[1, 1] if cov_matrix[1, 1] > 0 else 1.0
                else:
                    beta = 1.0
            except Exception:
                beta = 1.0
            
        alpha = ann_return - (risk_free + beta * ((1 + bench_returns.mean()) ** 252 - 1 - risk_free)) if not pd.isna(bench_returns.mean()) else 0
        
        # 5. Correlation Matrix
        corr_matrix = data[final_tickers].corr()
        corr_data = []
        for i, t1 in enumerate(final_tickers):
            for j, t2 in enumerate(final_tickers):
                val = corr_matrix.iloc[i, j]
                corr_data.append({"x": t1, "y": t2, "v": float(val) if not pd.isna(val) else 0.0})
                
        # 6. Moments
        skewness = stats.skew(port_returns) if len(port_returns) > 3 else 0
        kurtosis = stats.kurtosis(port_returns) if len(port_returns) > 3 else 0
        try:
            jb_stat, jb_p = stats.jarque_bera(port_returns) if len(port_returns) > 3 else (0, 1)
        except Exception:
            jb_p = 1.0
        
        # 7. Rolling Vol & Sharpe (63 days - quarterly)
        rolling_data = []
        if len(port_returns) >= 63:
            rolling_return = port_returns.rolling(63).mean() * 252
            rolling_vol = port_returns.rolling(63).std() * np.sqrt(252)
            rolling_sharpe = (rolling_return - risk_free) / rolling_vol
            
            for date in port_returns.index[62::5]: # Sample every 5 days
                if pd.notna(rolling_vol[date]) and pd.notna(rolling_sharpe[date]):
                    rolling_data.append({
                        "date": date.strftime('%Y-%m-%d'),
                        "volatility": float(rolling_vol[date]),
                        "sharpe": float(rolling_sharpe[date])
                    })
                
        # Drawdown chart data
        dd_data = []
        if not drawdowns.empty:
            for date in drawdowns.index[::max(1, len(drawdowns)//100)]: # Sample max 100 points
                dd_data.append({
                    "date": date.strftime('%Y-%m-%d'),
                    "drawdown": float(drawdowns[date])
                })
            
        # Composite Risk Score
        score_vol = min(ann_vol / 0.4 * 40, 40)
        score_dd = min(abs(max_drawdown) / 0.5 * 40, 40)
        score_beta = min(max(beta, 0) / 2.0 * 20, 20)
        risk_score = min(score_vol + score_dd + score_beta, 100)
        
        res = {
            "metrics": {
                "var_95": float(var_hist_95),
                "var_99": float(var_hist_99),
                "cvar_95": float(cvar_95),
                "max_drawdown": float(max_drawdown),
                "max_dd_duration_days": int(max_dd_duration),
                "sharpe": float(sharpe),
                "sortino": float(sortino),
                "calmar": float(calmar),
                "omega": float(omega),
                "beta": float(beta),
                "alpha": float(alpha),
                "volatility": float(ann_vol),
                "skewness": float(skewness),
                "kurtosis": float(kurtosis),
                "jarque_bera_p": float(jb_p)
            },
            "risk_score": float(risk_score),
            "correlation_matrix": corr_data,
            "rolling_metrics": rolling_data,
            "drawdown_curve": dd_data
        }
        return safe_json(res)
    return await loop.run_in_executor(None, _calc)

# --- STRESS TESTING ---

async def run_stress_test(portfolio: List[Dict[str, Any]]) -> Dict[str, float]:
    loop = asyncio.get_event_loop()
    def _calc():
        tickers = [item['ticker'] for item in portfolio]
        weights = np.array([item['weight'] for item in portfolio])
        
        # Normalize weights if needed
        if weights.sum() > 0:
            weights = weights / weights.sum()
        else:
            return {}

        scenarios = {
            "2008_GFC": ("2008-09-01", "2009-03-01"),
            "2020_COVID": ("2020-02-19", "2020-03-23"),
            "2022_RATE_HIKE": ("2022-01-01", "2022-12-31")
        }
        
        results = {}
        for name, (start, end) in scenarios.items():
            try:
                data = yf.download(tickers, start=start, end=end, progress=False)
                if data.empty:
                    results[name] = 0.0
                    continue
                
                # Handle MultiIndex and extract Close
                if 'Close' in data:
                    close_data = data['Close']
                else:
                    close_data = data.xs('Close', axis=1, level=0) if isinstance(data.columns, pd.MultiIndex) else data
                
                if isinstance(close_data, pd.Series):
                    close_data = close_data.to_frame()
                
                # Clean data
                close_data = close_data.ffill().bfill()
                
                if len(close_data) < 2:
                    results[name] = 0.0
                    continue

                # Calculate total return for the period per ticker
                start_prices = close_data.iloc[0]
                end_prices = close_data.iloc[-1]
                
                # Avoid division by zero
                ticker_returns = (end_prices - start_prices) / start_prices.replace(0, np.nan)
                ticker_returns = ticker_returns.fillna(0)
                
                # Match returns with weights
                port_return = 0
                for i, t in enumerate(tickers):
                    if t in ticker_returns.index:
                        port_return += ticker_returns[t] * weights[i]
                
                results[name] = float(port_return)
            except Exception as e:
                print(f"Stress test error for {name}: {e}")
                results[name] = 0.0
                
        return safe_json(results)
    return await loop.run_in_executor(None, _calc)

# --- FACTOR EXPOSURE ---

async def calculate_portfolio_factors(
    portfolio: List[Dict[str, Any]], 
    start_date: str = "2020-01-01",
    num_factors: int = 5,
    include_momentum: bool = True
) -> Dict[str, Any]:
    loop = asyncio.get_event_loop()
    def _calc():
        tickers = [item['ticker'] for item in portfolio]
        weights = np.array([item['weight'] for item in portfolio])
        
        factor_proxies = {
            "MKT": "SPY",
            "SMB_P": "IWM",
            "VALUE_P": "VTV",
            "GROWTH_P": "VUG",
            "QUAL": "QUAL",
            "CMA_P": "SPLV", # Proxy for Conservative
            "MOM": "MTUM"
        }
        
        all_tickers = list(set(tickers + list(factor_proxies.values())))
        try:
            raw_data = yf.download(all_tickers, start=start_date, progress=False)
            if raw_data.empty:
                return {}
            
            if 'Close' in raw_data:
                data = raw_data['Close']
            else:
                data = raw_data.xs('Close', axis=1, level=0) if isinstance(raw_data.columns, pd.MultiIndex) else raw_data
                
            if isinstance(data, pd.Series):
                data = data.to_frame()
                
            returns = data.pct_change().dropna()
            if returns.empty:
                return {}
            
            # Re-align portfolio weights
            available_portfolio = [t for t in tickers if t in returns.columns]
            if not available_portfolio:
                return {}
            
            port_weights = []
            for t in available_portfolio:
                idx = tickers.index(t)
                port_weights.append(weights[idx])
            
            port_weights = np.array(port_weights)
            if port_weights.sum() > 0:
                port_weights = port_weights / port_weights.sum()
            else:
                return {}

            port_returns = (returns[available_portfolio] * port_weights).sum(axis=1)
            
            # Construct Factors - ensure proxies exist
            def get_proxy_ret(name):
                ticker = factor_proxies.get(name)
                return returns[ticker] if ticker in returns.columns else port_returns * 0

            mkt = get_proxy_ret("MKT")
            smb = get_proxy_ret("SMB_P") - mkt
            hml = get_proxy_ret("VALUE_P") - get_proxy_ret("GROWTH_P")
            
            factors_dict = {
                'Market': mkt,
                'Size': smb,
                'Value': hml
            }
            
            if num_factors == 5:
                factors_dict['Quality'] = get_proxy_ret("QUAL") - mkt
                factors_dict['Investment'] = get_proxy_ret("CMA_P") - mkt
                
            if include_momentum:
                factors_dict['Momentum'] = get_proxy_ret("MOM") - mkt
                
            factors_df = pd.DataFrame(factors_dict)
            
            # OLS
            X = factors_df.copy()
            X['Intercept'] = 1.0
            y = port_returns
            
            # Align indices
            common_idx = X.index.intersection(y.index)
            if len(common_idx) < 10:
                return {}
                
            X = X.loc[common_idx]
            y = y.loc[common_idx]
            
            betas = np.linalg.lstsq(X.values, y.values, rcond=None)[0]
            
            # Beta mapping
            beta_results = {}
            for i, col in enumerate(factors_df.columns):
                beta_results[col] = float(betas[i])
            
            intercept = float(betas[-1])
            
            # Rolling 63-day Market Beta
            rolling_beta = []
            if 'Market' in X.columns and len(y) >= 63:
                for i in range(63, len(y) + 1):
                    window_y = y.iloc[i-63:i]
                    window_x = X.iloc[i-63:i]['Market']
                    var_x = np.var(window_x)
                    if var_x > 1e-9:
                        cov = np.cov(window_y, window_x)[0, 1]
                        rolling_beta.append({
                            "date": y.index[i-1].strftime('%Y-%m-%d'),
                            "beta": float(cov / var_x)
                        })
                
            # Attribution (Factor Return * Beta)
            ann_factor_returns = factors_df.mean() * 252
            attribution = {}
            for col in factors_df.columns:
                attribution[col] = float(beta_results[col] * ann_factor_returns[col])
                
            # R-Squared
            y_pred = X.values @ betas
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - y.mean()) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 1e-9 else 0
                
            res = {
                "betas": beta_results,
                "alpha": float(intercept * 252),
                "attribution": attribution,
                "rolling_beta": rolling_beta,
                "r_squared": float(r_squared)
            }
            return safe_json(res)
        except Exception as e:
            print(f"Factor calculation error: {e}")
            return {}
            
    return await loop.run_in_executor(None, _calc)

async def calculate_factors(ticker: str) -> Dict[str, float]:
    # Legacy wrapper for single ticker
    return await calculate_portfolio_factors([{"ticker": ticker, "weight": 1.0}])

# --- SCENARIO ANALYSIS ---

async def run_scenarios(portfolio: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    loop = asyncio.get_event_loop()
    def _calc():
        tickers = [item['ticker'] for item in portfolio]
        weights = np.array([item['weight'] for item in portfolio])
        
        # 1. Historical Scenarios
        hist_scenarios = {
            "2008 GFC": ("2008-09-01", "2009-03-01"),
            "2020 COVID": ("2020-02-15", "2020-04-15"),
            "2022 Rate Hikes": ("2022-01-01", "2022-12-31"),
            "2000 Dot-com": ("2000-03-01", "2001-03-01"),
            "1997 Asian Crisis": ("1997-07-01", "1998-01-01")
        }
        
        results = []
        all_tickers_plus_spy = list(set(tickers + ["SPY"]))
        
        for name, (start, end) in hist_scenarios.items():
            try:
                raw_data = yf.download(all_tickers_plus_spy, start=start, end=end, progress=False)
                if raw_data.empty: continue
                
                if 'Close' in raw_data:
                    data = raw_data['Close']
                else:
                    data = raw_data.xs('Close', axis=1, level=0) if isinstance(raw_data.columns, pd.MultiIndex) else raw_data
                
                if isinstance(data, pd.Series): data = data.to_frame()
                
                # Filter out tickers that have no data (mostly NaNs) for this specific historical period
                # (e.g. TSLA in 2000)
                valid_columns = []
                for col in data.columns:
                    if data[col].dropna().shape[0] > 5: # Need at least 5 data points
                        valid_columns.append(col)
                
                if not valid_columns: continue
                data = data[valid_columns].ffill().bfill()
                
                if len(data) < 2: continue
                
                rets = data.pct_change().fillna(0)
                
                available_tickers = [t for t in tickers if t in rets.columns]
                if not available_tickers: continue
                
                # Re-align weights
                scen_weights = []
                for t in available_tickers:
                    idx = tickers.index(t)
                    scen_weights.append(weights[idx])
                scen_weights = np.array(scen_weights)
                if scen_weights.sum() > 0:
                    scen_weights = scen_weights / scen_weights.sum()
                
                port_rets = (rets[available_tickers] * scen_weights).sum(axis=1)
                bench_rets = rets["SPY"] if "SPY" in rets.columns else rets.iloc[:, 0]
                
                port_cum = (1 + port_rets).cumprod() - 1
                bench_cum = (1 + bench_rets).cumprod() - 1
                
                total_impact = port_cum.iloc[-1]
                bench_impact = bench_cum.iloc[-1]
                
                worst_day_idx = port_rets.idxmin()
                worst_day_val = port_rets.loc[worst_day_idx]
                
                # Most affected positions
                asset_returns_period = (data[available_tickers].iloc[-1] / data[available_tickers].iloc[0].replace(0, np.nan)) - 1
                asset_returns_period = asset_returns_period.fillna(0)
                
                most_affected_list = []
                for t in available_tickers:
                    most_affected_list.append({
                        "ticker": t,
                        "impact": float(asset_returns_period[t])
                    })
                most_affected_list.sort(key=lambda x: x["impact"])
                
                results.append({
                    "name": name,
                    "type": "Historical",
                    "your_portfolio_impact": float(total_impact),
                    "benchmark_impact": float(bench_impact),
                    "impact_pct": float(total_impact),
                    "worst_day_val": float(worst_day_val),
                    "worst_day_date": worst_day_idx.strftime('%Y-%m-%d'),
                    "most_affected_positions": most_affected_list,
                    "recovery_est_days": int(len(port_rets) / 2)
                })
            except Exception as e:
                print(f"Scenario error for {name}: {e}")
                continue
                
        # 2. Hypothetical shocks
        shocks = [
            {"name": "Rates +300bps", "impact_factor": -0.05},
            {"name": "Oil +100%", "impact_factor": 0.08},
            {"name": "USD +20%", "impact_factor": -0.03},
            {"name": "Market Crash -30%", "impact_factor": -0.30},
            {"name": "Inflation +5%", "impact_factor": -0.04}
        ]
        
        try:
            # Fetch 1y market beta for hypothetical calculations
            end_dt = datetime.now()
            start_dt = end_dt - timedelta(days=365)
            raw_beta_data = yf.download(all_tickers_plus_spy, start=start_dt, end=end_dt, progress=False)
            
            if not raw_beta_data.empty:
                if 'Close' in raw_beta_data:
                    beta_data = raw_beta_data['Close']
                else:
                    beta_data = raw_beta_data.xs('Close', axis=1, level=0) if isinstance(raw_beta_data.columns, pd.MultiIndex) else raw_beta_data
                
                if isinstance(beta_data, pd.Series): beta_data = beta_data.to_frame()
                beta_rets = beta_data.pct_change().dropna()
                
                for shock in shocks:
                    shock_impact = 0
                    affected_positions = []
                    
                    for i, t in enumerate(tickers):
                        w = weights[i]
                        if t in beta_rets.columns and "SPY" in beta_rets.columns:
                            spy_var = np.var(beta_rets["SPY"])
                            if spy_var > 1e-9:
                                beta = np.cov(beta_rets[t], beta_rets["SPY"])[0, 1] / spy_var
                            else:
                                beta = 1.0
                            asset_impact = shock['impact_factor'] * beta
                        else:
                            asset_impact = shock['impact_factor']
                        
                        shock_impact += asset_impact * w
                        affected_positions.append({"ticker": t, "impact": float(asset_impact)})
                    
                    affected_positions.sort(key=lambda x: x["impact"])
                    
                    scenario_res = {
                        "name": shock['name'],
                        "type": "Hypothetical",
                        "your_portfolio_impact": float(shock_impact),
                        "benchmark_impact": float(shock['impact_factor']),
                        "impact_pct": float(shock_impact),
                        "worst_day_val": float(shock_impact / 5),
                        "worst_day_date": datetime.now().strftime('%Y-%m-%d'),
                        "most_affected_positions": affected_positions,
                        "recovery_est_days": 180
                    }
                    
                    if shock['name'] == "Market Crash -30%":
                        scenario_res["correlations"] = {"avg_correlation": 0.92, "is_spike": True}
                        
                    results.append(scenario_res)
        except Exception as e:
            print(f"Hypothetical shock calculation error: {e}")
            
        return safe_json(results)
    return await loop.run_in_executor(None, _calc)