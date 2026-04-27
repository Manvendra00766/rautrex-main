import numpy as np
import pandas as pd
from scipy.stats import norm
import yfinance as yf
from typing import Dict, Any, List, Optional
import asyncio
from datetime import datetime
from utils import clean_nans

# --- OPTION PRICING MODELS ---

def _black_scholes(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call'):
    # Safety checks
    if S <= 0 or K <= 0 or sigma <= 0:
        intrinsic = max(0.0, S - K) if option_type == 'call' else max(0.0, K - S)
        return {
            "price": float(intrinsic),
            "greeks": {"delta": 0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0, "vanna": 0, "volga": 0, "charm": 0},
            "intrinsic_value": float(intrinsic), "time_value": 0.0
        }
    
    if T <= 1e-6:
        intrinsic = max(0.0, S - K) if option_type == 'call' else max(0.0, K - S)
        return {
            "price": float(intrinsic),
            "greeks": {"delta": 1.0 if option_type == 'call' and S > K else 0.0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0, "vanna": 0, "volga": 0, "charm": 0},
            "intrinsic_value": float(intrinsic), "time_value": 0.0
        }
    
    try:
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        if option_type == 'call':
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            delta = norm.cdf(d1)
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
            rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100
        else:
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            delta = norm.cdf(d1) - 1
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
            
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        vega = S * np.sqrt(T) * norm.pdf(d1) / 100
        
        vanna = -norm.pdf(d1) * d2 / sigma if sigma > 0 else 0
        volga = S * np.sqrt(T) * norm.pdf(d1) * d1 * d2 / sigma if sigma > 0 else 0
        charm = -norm.pdf(d1) * (r / (sigma * np.sqrt(T)) - d2 / (2 * T)) if sigma > 0 and T > 0 else 0
        
        intrinsic = max(0.0, S - K) if option_type == 'call' else max(0.0, K - S)
        time_value = max(0.0, price - intrinsic)

        return {
            "price": float(price),
            "greeks": {
                "delta": float(delta), "gamma": float(gamma), "theta": float(theta),
                "vega": float(vega), "rho": float(rho), "vanna": float(vanna),
                "volga": float(volga), "charm": float(charm)
            },
            "intrinsic_value": float(intrinsic),
            "time_value": float(time_value)
        }
    except Exception as e:
        print(f"BS Error: {e}")
        return {"price": 0, "greeks": {"delta": 0, "gamma": 0, "theta": 0, "vega": 0, "rho": 0}, "intrinsic_value": 0, "time_value": 0}

def _binomial_tree(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call', steps: int = 50, european: bool = False):
    if T <= 0 or sigma <= 0 or S <= 0:
        return _black_scholes(S, K, T, r, sigma, option_type)
        
    try:
        dt = T / steps
        u = np.exp(sigma * np.sqrt(dt))
        d = 1 / u
        p = (np.exp(r * dt) - d) / (u - d)
        
        if p > 1 or p < 0: # Non-arbitrage violation in tree
            return _black_scholes(S, K, T, r, sigma, option_type)

        prices = S * (u ** np.arange(steps, -1, -1)) * (d ** np.arange(0, steps + 1, 1))
        
        if option_type == 'call':
            values = np.maximum(0, prices - K)
        else:
            values = np.maximum(0, K - prices)
            
        for i in range(steps - 1, -1, -1):
            values = np.exp(-r * dt) * (p * values[:-1] + (1 - p) * values[1:])
            if not european:
                prices = S * (u ** np.arange(i, -1, -1)) * (d ** np.arange(0, i + 1, 1))
                if option_type == 'call':
                    values = np.maximum(values, prices - K)
                else:
                    values = np.maximum(values, K - prices)
                    
        bs_res = _black_scholes(S, K, T, r, sigma, option_type)
        intrinsic = max(0.0, S - K) if option_type == 'call' else max(0.0, K - S)
        return {
            "price": float(values[0]),
            "greeks": bs_res['greeks'],
            "intrinsic_value": float(intrinsic),
            "time_value": float(max(0.0, values[0] - intrinsic))
        }
    except Exception:
        return _black_scholes(S, K, T, r, sigma, option_type)

def _monte_carlo_options(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call', simulations: int = 5000):
    if T <= 0 or sigma <= 0 or S <= 0:
        return _black_scholes(S, K, T, r, sigma, option_type)
        
    try:
        z = np.random.standard_normal(simulations)
        ST = S * np.exp((r - 0.5 * sigma ** 2) * T + sigma * np.sqrt(T) * z)
        
        if option_type == 'call':
            payoffs = np.maximum(0, ST - K)
        else:
            payoffs = np.maximum(0, K - ST)
            
        price = np.exp(-r * T) * np.mean(payoffs)
        bs_res = _black_scholes(S, K, T, r, sigma, option_type)
        intrinsic = max(0.0, S - K) if option_type == 'call' else max(0.0, K - S)
        
        return {
            "price": float(price),
            "greeks": bs_res['greeks'],
            "intrinsic_value": float(intrinsic),
            "time_value": float(max(0.0, price - intrinsic))
        }
    except Exception:
        return _black_scholes(S, K, T, r, sigma, option_type)

async def price_option(model: str, option_type: str, S: float, K: float, T: float, r: float, sigma: float, heston_params: Dict = None):
    loop = asyncio.get_event_loop()
    def _price():
        if model == 'black_scholes':
            res = _black_scholes(S, K, T, r, sigma, option_type)
        elif model == 'binomial':
            res = _binomial_tree(S, K, T, r, sigma, option_type)
        elif model == 'monte_carlo':
            res = _monte_carlo_options(S, K, T, r, sigma, option_type)
        elif model == 'heston':
            hp = heston_params or {"v0": sigma**2, "kappa": 2.0, "theta": sigma**2, "sigma": 0.3, "rho": -0.5}
            v0, kappa, theta, sig, rho = hp['v0'], hp['kappa'], hp['theta'], hp['sigma'], hp['rho']
            # Simplified Heston via drift-adjusted sigma
            v_avg = theta + (v0 - theta) * (1 - np.exp(-kappa * T)) / (kappa * T) if kappa * T > 0 else v0
            res = _black_scholes(S, K, T, r, np.sqrt(max(0.0001, v_avg)), option_type)
        else:
            res = _black_scholes(S, K, T, r, sigma, option_type)
        return clean_nans(res)
    return await loop.run_in_executor(None, _price)

# --- OPTIONS CHAIN ---

async def fetch_options_chain(ticker: str):
    loop = asyncio.get_event_loop()
    def _fetch():
        try:
            tk = yf.Ticker(ticker)
            expirations = tk.options
            if not expirations:
                return {"expirations": [], "calls": [], "puts": [], "spot": 0}
            
            opt = tk.option_chain(expirations[0])
            calls = opt.calls[['strike', 'lastPrice', 'bid', 'ask', 'impliedVolatility']].fillna(0).to_dict('records')
            puts = opt.puts[['strike', 'lastPrice', 'bid', 'ask', 'impliedVolatility']].fillna(0).to_dict('records')
            
            hist = tk.history(period="1d")
            spot = float(hist['Close'].iloc[-1]) if not hist.empty else 0.0
            
            return clean_nans({
                "spot": spot,
                "expirations": list(expirations),
                "current_expiration": expirations[0],
                "calls": calls, "puts": puts
            })
        except Exception as e:
            print(f"Chain Error: {e}")
            return {"error": str(e), "calls": [], "puts": []}
    return await loop.run_in_executor(None, _fetch)

# --- STRATEGY PNL ---

async def calculate_strategy_pnl(name: str, spot: float, legs: List[Dict]):
    loop = asyncio.get_event_loop()
    def _calc():
        if spot <= 0: return {"error": "Invalid spot price"}
        s_range = np.linspace(spot * 0.5, spot * 1.5, 100)
        pnl = np.zeros_like(s_range)
        for leg in legs:
            K, prem, pos, side = leg['strike'], leg['premium'], leg['position'], leg['type']
            if side == 'call': payoff = np.maximum(0, s_range - K)
            elif side == 'put': payoff = np.maximum(0, K - s_range)
            else: payoff = s_range - K
            pnl += pos * (payoff - prem)
        
        return clean_nans({
            "strategy": name,
            "chart_data": [{"underlying": float(s), "pnl": float(p)} for s, p in zip(s_range, pnl)],
            "max_profit": float(np.max(pnl)), "max_loss": float(np.min(pnl))
        })
    return await loop.run_in_executor(None, _calc)

# --- IV SURFACE ---

async def generate_iv_surface(ticker: str):
    loop = asyncio.get_event_loop()
    def _surf():
        try:
            tk = yf.Ticker(ticker)
            exps = tk.options[:4]
            if not exps: return {}
            spot = tk.history(period="1d")['Close'].iloc[-1]
            
            data = []
            strikes_all = set()
            for exp in exps:
                chain = tk.option_chain(exp)
                c = chain.calls
                c = c[(c['strike'] > spot*0.8) & (c['strike'] < spot*1.2)]
                dte = (datetime.strptime(exp, '%Y-%m-%d') - datetime.now()).days / 365.0
                if dte <= 0: dte = 0.01
                for _, r in c.iterrows():
                    data.append({"dte": dte, "strike": r['strike'], "iv": r['impliedVolatility']})
                    strikes_all.add(r['strike'])
            
            df = pd.DataFrame(data)
            if df.empty: return {}
            
            z_strikes = sorted(list(strikes_all))
            y_exps = sorted(list(df['dte'].unique()))
            grid = []
            for d in y_exps:
                row = []
                sub = df[df['dte'] == d]
                for s in z_strikes:
                    match = sub[sub['strike'] == s]
                    row.append(float(match['iv'].iloc[0]) if not match.empty else 0.0)
                grid.append(row)
                
            return clean_nans({
                "iv_surface": {"strikes": z_strikes, "expiries": [int(y*365) for y in y_exps], "iv_grid": grid}
            })
        except Exception as e:
            print(f"Surface Error: {e}")
            return {}
    return await loop.run_in_executor(None, _surf)
