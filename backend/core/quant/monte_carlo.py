import numpy as np
from typing import Tuple

class MonteCarloEngine:
    def __init__(self, num_simulations: int = 1000, time_horizon: int = 252):
        self.num_simulations = num_simulations
        self.time_horizon = time_horizon # Days

    def simulate_gbm(self, S0: float, mu: float, sigma: float, dt: float = 1/252) -> np.ndarray:
        """
        Simulate Geometric Brownian Motion for a single asset.
        S0: Initial price
        mu: Expected annualized return
        sigma: Annualized volatility
        """
        # Array of random normal variables (Z)
        Z = np.random.standard_normal((self.time_horizon, self.num_simulations))
        
        # Pre-calculate the drift component
        drift = (mu - 0.5 * sigma**2) * dt
        
        # Calculate daily returns
        daily_returns = np.exp(drift + sigma * np.sqrt(dt) * Z)
        
        # Pre-allocate price array
        price_paths = np.zeros((self.time_horizon + 1, self.num_simulations))
        price_paths[0] = S0
        
        # Calculate price paths
        for t in range(1, self.time_horizon + 1):
            price_paths[t] = price_paths[t-1] * daily_returns[t-1]
            
        return price_paths

    def simulate_correlated_portfolio(self, 
                                      initial_prices: np.ndarray, 
                                      expected_returns: np.ndarray, 
                                      cov_matrix: np.ndarray, 
                                      dt: float = 1/252) -> np.ndarray:
        """
        Simulate correlated Geometric Brownian Motion for a portfolio.
        Returns array of shape (time_horizon + 1, num_assets, num_simulations)
        """
        num_assets = len(initial_prices)
        
        # Cholesky decomposition to get lower triangular matrix L
        L = np.linalg.cholesky(cov_matrix)
        
        # Pre-allocate array
        paths = np.zeros((self.time_horizon + 1, num_assets, self.num_simulations))
        paths[0] = initial_prices[:, np.newaxis]
        
        for t in range(1, self.time_horizon + 1):
            # Independent standard normal variables
            Z = np.random.standard_normal((num_assets, self.num_simulations))
            
            # Correlated random variables: L * Z
            correlated_Z = L.dot(Z)
            
            # Drift for each asset
            drift = (expected_returns - 0.5 * np.diag(cov_matrix)) * dt
            drift = drift[:, np.newaxis]
            
            # Volatility component
            vol = np.sqrt(dt) * correlated_Z
            
            # Daily change factor
            daily_change = np.exp(drift + vol)
            
            paths[t] = paths[t-1] * daily_change
            
        return paths

    def calculate_var_cvar(self, final_portfolio_values: np.ndarray, initial_value: float, confidence_level: float = 0.95) -> Tuple[float, float]:
        """Calculates Monte Carlo VaR and CVaR from simulation results."""
        portfolio_returns = (final_portfolio_values - initial_value) / initial_value
        
        var_percentile = np.percentile(portfolio_returns, (1 - confidence_level) * 100)
        cvar_value = portfolio_returns[portfolio_returns <= var_percentile].mean()
        
        return var_percentile, cvar_value if not np.isnan(cvar_value) else var_percentile
