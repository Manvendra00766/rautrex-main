import numpy as np
from scipy.stats import norm
from typing import Dict, Any
from core.financial_constants import RISK_FREE_RATE

class DerivativesEngine:
    def __init__(self, risk_free_rate: float = RISK_FREE_RATE):
        self.risk_free_rate = risk_free_rate

    def _d1_d2(self, S: float, K: float, T: float, sigma: float) -> tuple:
        """Calculate d1 and d2 for Black-Scholes."""
        if T <= 0 or sigma <= 0:
            return 0.0, 0.0
        d1 = (np.log(S / K) + (self.risk_free_rate + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return d1, d2

    def black_scholes_price(self, option_type: str, S: float, K: float, T: float, sigma: float) -> float:
        """
        Calculate Black-Scholes option price.
        S: Spot price
        K: Strike price
        T: Time to maturity (in years)
        sigma: Volatility (annualized)
        option_type: 'call' or 'put'
        """
        if T <= 0:
            return max(0.0, S - K) if option_type == 'call' else max(0.0, K - S)
        
        d1, d2 = self._d1_d2(S, K, T, sigma)
        
        if option_type == 'call':
            price = S * norm.cdf(d1) - K * np.exp(-self.risk_free_rate * T) * norm.cdf(d2)
        elif option_type == 'put':
            price = K * np.exp(-self.risk_free_rate * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        else:
            raise ValueError("option_type must be 'call' or 'put'")
            
        return price

    def calculate_greeks(self, option_type: str, S: float, K: float, T: float, sigma: float) -> Dict[str, float]:
        """Calculate Option Greeks."""
        if T <= 0 or sigma <= 0:
            return {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}

        d1, d2 = self._d1_d2(S, K, T, sigma)
        
        # Delta
        if option_type == 'call':
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1

        # Gamma
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        
        # Theta (annualized)
        term1 = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
        if option_type == 'call':
            term2 = self.risk_free_rate * K * np.exp(-self.risk_free_rate * T) * norm.cdf(d2)
            theta = term1 - term2
        else:
            term2 = self.risk_free_rate * K * np.exp(-self.risk_free_rate * T) * norm.cdf(-d2)
            theta = term1 + term2
            
        # Vega
        vega = S * norm.pdf(d1) * np.sqrt(T)
        
        # Rho
        if option_type == 'call':
            rho = K * T * np.exp(-self.risk_free_rate * T) * norm.cdf(d2)
        else:
            rho = -K * T * np.exp(-self.risk_free_rate * T) * norm.cdf(-d2)

        return {
            "delta": delta,
            "gamma": gamma,
            "theta": theta, # Per year
            "vega": vega,   # Per 100% vol change
            "rho": rho      # Per 100% rate change
        }

    def binomial_tree_price(self, option_type: str, is_american: bool, S: float, K: float, T: float, sigma: float, N: int = 100) -> float:
        """Calculate option price using Cox-Ross-Rubinstein Binomial Tree."""
        dt = T / N
        u = np.exp(sigma * np.sqrt(dt))
        d = 1 / u
        p = (np.exp(self.risk_free_rate * dt) - d) / (u - d)
        
        # Price tree at maturity
        prices = np.zeros(N + 1)
        for i in range(N + 1):
            prices[i] = S * (u ** (N - i)) * (d ** i)
            
        # Option value tree at maturity
        values = np.zeros(N + 1)
        for i in range(N + 1):
            if option_type == 'call':
                values[i] = max(0, prices[i] - K)
            else:
                values[i] = max(0, K - prices[i])
                
        # Step backwards
        for j in range(N - 1, -1, -1):
            for i in range(j + 1):
                # Expected value
                values[i] = np.exp(-self.risk_free_rate * dt) * (p * values[i] + (1 - p) * values[i + 1])
                if is_american:
                    # Early exercise check
                    current_price = S * (u ** (j - i)) * (d ** i)
                    if option_type == 'call':
                        values[i] = max(values[i], current_price - K)
                    else:
                        values[i] = max(values[i], K - current_price)
                        
        return values[0]
