import numpy as np
import pandas as pd
import yfinance as yf
from scipy.optimize import minimize
import asyncio
from typing import List, Dict, Any, Optional
from utils import safe_json

# --- CORE MATH UTILS ---

def calculate_position_metrics(position, current_price):
    shares = position["shares"]
    avg_cost = position["avg_cost_price"]  # per share
    market_value = shares * current_price
    cost_basis = shares * avg_cost
    pnl = market_value - cost_basis
    return_pct = ((current_price - avg_cost) / avg_cost) * 100 if avg_cost > 0 else 0
    return {
        "market_value": round(market_value, 2),
        "cost_basis": round(cost_basis, 2),
        "pnl": round(pnl, 2),
        "return_pct": round(return_pct, 2)
    }

def get_portfolio_performance(weights, mean_returns, cov_matrix, risk_free_rate=0.065):
    returns = np.sum(mean_returns * weights) * 252
    std = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(252)
    sharpe = (returns - risk_free_rate) / std if std != 0 else 0
    return returns, std, sharpe

# --- OPTIMIZATION METHODS ---

def min_volatility(weights, mean_returns, cov_matrix):
    return get_portfolio_performance(weights, mean_returns, cov_matrix)[1]

def neg_sharpe(weights, mean_returns, cov_matrix, risk_free_rate=0.065):
    return -get_portfolio_performance(weights, mean_returns, cov_matrix, risk_free_rate)[2]

def risk_parity_objective(weights, cov_matrix):
    # Equal risk contribution
    # Risk contribution = w * (Cov * w) / Port_Vol
    # We minimize the sum of squared differences of risk contributions
    n = len(weights)
    port_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    risk_contributions = weights * np.dot(cov_matrix, weights) / port_vol
    target = port_vol / n
    return np.sum(np.square(risk_contributions - target))

# --- SERVICE CLASS ---

def _get_returns(tickers: List[str], period: str = "2y") -> pd.DataFrame:
    try:
        data = yf.download(tickers, period=period, progress=False)
        if data.empty:
            return pd.DataFrame()
        
        # Handle MultiIndex vs Single Index
        if 'Close' in data.columns:
            prices = data['Close']
        else:
            # Fallback if yfinance structure varies (e.g. single ticker with only Close)
            prices = data.xs('Close', axis=1, level=0) if isinstance(data.columns, pd.MultiIndex) else data
            
        if isinstance(prices, pd.Series):
            prices = prices.to_frame()
            if len(tickers) == 1:
                prices.columns = tickers
        
        returns = prices.pct_change().dropna()
        return returns
    except Exception as e:
        print(f"Error fetching portfolio data: {e}")
        return pd.DataFrame()

async def optimize_portfolio_logic(
    tickers: List[str],
    method: str = "markowitz",
    objective: str = "max_sharpe",
    constraints: Optional[Dict] = None,
    risk_free_rate: float = 0.065
):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _optimize, tickers, method, objective, constraints, risk_free_rate)

def _optimize(tickers, method, objective, constraints_data, risk_free_rate):
    # 1. Fetch Data
    returns = _get_returns(tickers, "2y")
    
    if returns.empty or (len(returns) < 5):
        raise ValueError(f"Insufficient data for tickers: {tickers}")
        
    # Ensure we only use tickers present in data
    available_tickers = [t for t in tickers if t in returns.columns]
    if not available_tickers:
        raise ValueError("No valid ticker data found.")
    
    returns = returns[available_tickers]
    mean_returns = returns.mean()
    cov_matrix = returns.cov()
    
    n = len(available_tickers)
    init_weights = np.array([1.0/n] * n)
    
    # 2. Define Constraints
    bounds = tuple((0.0, 1.0) for _ in range(n))
    if constraints_data and 'bounds' in constraints_data:
        bounds = tuple((constraints_data['bounds'].get(t, [0.0, 1.0])[0], 
                        constraints_data['bounds'].get(t, [0.0, 1.0])[1]) for t in available_tickers)
        
    cons = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0})
    
    # 3. Solve
    try:
        if method == "markowitz":
            if objective == "max_sharpe":
                opt = minimize(neg_sharpe, init_weights, args=(mean_returns, cov_matrix, risk_free_rate), 
                               method='SLSQP', bounds=bounds, constraints=cons)
            elif objective == "min_vol":
                opt = minimize(min_volatility, init_weights, args=(mean_returns, cov_matrix), 
                               method='SLSQP', bounds=bounds, constraints=cons)
            else: # max_return
                opt = minimize(lambda x: -np.sum(mean_returns * x), init_weights, 
                               method='SLSQP', bounds=bounds, constraints=cons)
        
        elif method == "risk_parity":
            opt = minimize(risk_parity_objective, init_weights, args=(cov_matrix,), 
                           method='SLSQP', bounds=bounds, constraints=cons)
        
        elif method == "max_diversification":
            def neg_div_ratio(w, cov):
                vol = np.sqrt(np.dot(w.T, np.dot(cov, w)))
                sum_vol = np.sum(w * np.sqrt(np.diag(cov)))
                return -sum_vol / vol if vol > 1e-9 else 0
            opt = minimize(neg_div_ratio, init_weights, args=(cov_matrix,), 
                           method='SLSQP', bounds=bounds, constraints=cons)
        else:
            opt = minimize(neg_sharpe, init_weights, args=(mean_returns, cov_matrix, risk_free_rate), 
                           method='SLSQP', bounds=bounds, constraints=cons)
    except Exception as e:
        print(f"Solver Error: {e}")
        # Fallback to equal weights
        class DummyOpt:
            def __init__(self, x): self.x = x
        opt = DummyOpt(init_weights)

    opt_weights = opt.x
    ret, vol, sharpe = get_portfolio_performance(opt_weights, mean_returns, cov_matrix, risk_free_rate)
    
    # Risk Contributions
    # Corrected denominator: ensure vol is scaled for the period if needed, 
    # but here we use annual vol and annual cov
    ann_cov = cov_matrix * 252
    risk_contributions = (opt_weights * np.dot(ann_cov, opt_weights)) / vol if vol > 1e-9 else opt_weights * 0
    risk_cont_percent = risk_contributions / vol if vol > 1e-9 else opt_weights * 0
    
    weight_details = []
    for i, t in enumerate(available_tickers):
        weight_details.append({
            "ticker": t,
            "weight": float(opt_weights[i]),
            "expected_return": float(mean_returns[t] * 252),
            "volatility": float(np.sqrt(cov_matrix.iloc[i, i]) * np.sqrt(252)),
            "risk_contribution": float(risk_cont_percent[i])
        })

    # 4. Compute Efficient Frontier
    frontier = []
    if method == "markowitz":
        try:
            target_returns = np.linspace(mean_returns.min() * 252, mean_returns.max() * 252, 20)
            for tr in target_returns:
                c = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1.0},
                     {'type': 'eq', 'fun': lambda x: np.sum(mean_returns * x) * 252 - tr})
                res = minimize(min_volatility, init_weights, args=(mean_returns, cov_matrix), 
                               method='SLSQP', bounds=bounds, constraints=c)
                if res.success:
                    f_ret, f_vol, f_sharpe = get_portfolio_performance(res.x, mean_returns, cov_matrix, risk_free_rate)
                    frontier.append({
                        "volatility": float(f_vol),
                        "return": float(f_ret),
                        "sharpe": float(f_sharpe),
                        "weights": {available_tickers[i]: float(res.x[i]) for i in range(len(available_tickers))}
                    })
        except Exception:
            pass

    # 5. Random Portfolios
    random_portfolios = []
    for _ in range(100):
        w = np.random.random(n)
        w /= np.sum(w)
        r, v, s = get_portfolio_performance(w, mean_returns, cov_matrix, risk_free_rate)
        random_portfolios.append({"volatility": float(v), "return": float(r)})

    res = {
        "optimal_weights": {available_tickers[i]: float(opt_weights[i]) for i in range(len(available_tickers))},
        "weight_details": weight_details,
        "metrics": {
            "return": float(ret),
            "volatility": float(vol),
            "sharpe": float(sharpe),
            "diversification_ratio": float(1.0) # Placeholder
        },
        "frontier": frontier,
        "random_portfolios": random_portfolios
    }
    return safe_json(res)

async def get_correlation_matrix(tickers: List[str]):
    loop = asyncio.get_event_loop()
    def _calc():
        returns = _get_returns(tickers, "1y")
        if returns.empty:
            return []
        corr = returns.corr()
        res = []
        for i, t1 in enumerate(returns.columns):
            for j, t2 in enumerate(returns.columns):
                res.append({"x": t1, "y": t2, "v": float(corr.iloc[i, j])})
        return safe_json(res)
    return await loop.run_in_executor(None, _calc)

# --- REBALANCING ---

async def calculate_rebalance(
    current_positions: List[Dict[str, Any]],
    target_weights: Dict[str, float],
    threshold: float = 0.05,
    total_value: Optional[float] = None
):
    loop = asyncio.get_event_loop()
    def _calc():
        tickers = list(target_weights.keys())
        data = yf.download(tickers, period="5d", progress=False)
        
        if 'Close' in data.columns:
            close_data = data['Close']
        else:
            close_data = data.xs('Close', axis=1, level=0) if isinstance(data.columns, pd.MultiIndex) else data
            
        current_prices = {}
        if isinstance(close_data, pd.DataFrame):
            if not close_data.empty:
                current_prices = close_data.iloc[-1].to_dict()
        elif isinstance(close_data, pd.Series):
            current_prices = {tickers[0]: close_data.iloc[-1]}
        
        # Ensure prices for all tickers
        for t in tickers:
            if t not in current_prices or pd.isna(current_prices[t]):
                current_prices[t] = 100.0 # Extreme fallback

        if total_value is None:
            calc_total = sum(p['shares'] * current_prices.get(p['ticker'], 0) for p in current_positions)
        else:
            calc_total = total_value
            
        current_weights = {}
        for p in current_positions:
            val = p['shares'] * current_prices.get(p['ticker'], 0)
            current_weights[p['ticker']] = val / calc_total if calc_total > 0 else 0
            
        for t in tickers:
            if t not in current_weights:
                current_weights[t] = 0.0
                
        drift = {}
        trades = []
        post_rebalance_weights = {}
        
        for t in tickers:
            curr_w = current_weights.get(t, 0)
            target_w = target_weights.get(t, 0)
            d = curr_w - target_w
            drift[t] = d
            
            if abs(d) > threshold:
                target_val = calc_total * target_w
                curr_val = calc_total * curr_w
                trade_val = target_val - curr_val
                price = current_prices.get(t, 0)
                shares = trade_val / price if price > 0 else 0
                
                trades.append({
                    "ticker": t,
                    "action": "BUY" if trade_val > 0 else "SELL",
                    "amount": float(abs(trade_val)),
                    "shares": float(abs(shares)),
                    "price": float(price),
                    "estimated_cost": float(abs(trade_val) * 0.001)
                })
                post_rebalance_weights[t] = target_w
            else:
                post_rebalance_weights[t] = curr_w
                
        return safe_json({
            "current_weights": current_weights,
            "target_weights": target_weights,
            "post_rebalance_weights": post_rebalance_weights,
            "drift": drift,
            "trades": trades,
            "total_value": float(calc_total),
            "total_estimated_cost": float(sum(t['estimated_cost'] for t in trades))
        })
    return await loop.run_in_executor(None, _calc)

async def backtest_rebalance(
    tickers: List[str],
    target_weights: Dict[str, float],
    frequency: str = "monthly",
    start_date: str = "2020-01-01",
    initial_capital: float = 100000
):
    loop = asyncio.get_event_loop()
    def _calc():
        data = yf.download(tickers, start=start_date, progress=False)
        
        if 'Close' in data.columns:
            prices = data['Close']
        else:
            prices = data.xs('Close', axis=1, level=0) if isinstance(data.columns, pd.MultiIndex) else data
            
        if isinstance(prices, pd.Series):
            prices = prices.to_frame()
            prices.columns = tickers

        returns = prices.pct_change().fillna(0)
        
        freq_map = {"monthly": "ME", "quarterly": "QE", "annual": "YE"}
        rebalance_dates = returns.resample(freq_map.get(frequency, "ME")).last().index
        
        # Valid tickers check
        available_tickers = [t for t in tickers if t in returns.columns]
        if not available_tickers:
            raise ValueError("No valid tickers found for backtest.")
            
        target_series = pd.Series({t: target_weights.get(t, 0) for t in available_tickers})
        target_series = target_series / target_series.sum()

        portfolio_no_reb = initial_capital * (1 + returns[available_tickers].dot(target_series)).cumprod()
        
        portfolio_reb = []
        current_value = initial_capital
        current_weights = target_series.copy()
        annual_stats = {}
        
        for date, row in returns[available_tickers].iterrows():
            year = date.year
            if year not in annual_stats:
                annual_stats[year] = {"reb_val_start": current_value, "noreb_val_start": portfolio_no_reb.loc[date], "cost": 0}
            
            asset_values = current_value * current_weights * (1 + row)
            current_value = asset_values.sum()
            current_weights = asset_values / current_value if current_value > 0 else asset_values * 0
            
            if date in rebalance_dates:
                target_values = current_value * target_series
                turnover = np.sum(np.abs(target_values - asset_values))
                cost = turnover * 0.001
                current_value -= cost
                annual_stats[year]["cost"] += cost
                current_weights = target_series.copy()
                
            portfolio_reb.append(current_value)
            annual_stats[year]["reb_val_end"] = current_value
            annual_stats[year]["noreb_val_end"] = portfolio_no_reb.loc[date]
            
        portfolio_reb = pd.Series(portfolio_reb, index=returns.index)
        
        annual_list = []
        for y, s in annual_stats.items():
            reb_ret = (s["reb_val_end"] / s["reb_val_start"]) - 1 if s["reb_val_start"] > 0 else 0
            noreb_ret = (s["noreb_val_end"] / s["noreb_val_start"]) - 1 if s["noreb_val_start"] > 0 else 0
            annual_list.append({
                "year": y,
                "rebalanced_return": float(reb_ret),
                "unrebalanced_return": float(noreb_ret),
                "rebalancing_cost": float(s["cost"])
            })

        def get_metrics(perf):
            ret = (perf.iloc[-1] / perf.iloc[0]) - 1 if perf.iloc[0] > 0 else 0
            ann_ret = (1 + ret) ** (252 / len(perf)) - 1 if len(perf) > 0 else 0
            v_rets = perf.pct_change().dropna()
            vol = v_rets.std() * np.sqrt(252) if not v_rets.empty else 0
            sharpe = ann_ret / vol if vol > 1e-9 else 0
            dd = (perf / perf.cummax()) - 1
            max_dd = dd.min() if not dd.empty else 0
            return {"total_return": float(ret), "ann_return": float(ann_ret), "vol": float(vol), "sharpe": float(sharpe), "max_dd": float(max_dd)}

        res = {
            "no_rebalance": get_metrics(portfolio_no_reb),
            "rebalanced": get_metrics(portfolio_reb),
            "annual_metrics": annual_list,
            "total_rebalancing_costs": float(sum(a['rebalancing_cost'] for a in annual_list)),
            "equity_curve": [
                {"date": d.strftime('%Y-%m-%d'), "no_reb": float(v1), "reb": float(v2)}
                for d, v1, v2 in zip(returns.index[::max(1, len(returns)//100)], portfolio_no_reb[::max(1, len(returns)//100)], portfolio_reb[::max(1, len(returns)//100)])
            ]
        }
        return safe_json(res)
    return await loop.run_in_executor(None, _calc)