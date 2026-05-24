import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, List, Tuple, Any
from core.financial_constants import RISK_FREE_RATE

class PortfolioOptimizer:
    """
    NOTE: Do not add calculate_sortino_ratio here.
    All Sortino calculations must use PortfolioCalculationService.calculate_sortino_ratio
    which is the Single Source of Truth for risk-adjusted return metrics.
    """
    def __init__(self, risk_free_rate: float = RISK_FREE_RATE):
        self.risk_free_rate = risk_free_rate

    def calculate_returns_and_cov(self, price_data: pd.DataFrame) -> Tuple[pd.Series, pd.DataFrame]:
        """Calculates expected annualized returns and covariance matrix from daily prices."""
        daily_returns = price_data.pct_change().dropna()
        # Annualized expected return
        expected_returns = daily_returns.mean() * 252
        # Annualized covariance
        cov_matrix = daily_returns.cov() * 252
        return expected_returns, cov_matrix

    def portfolio_performance(self, weights: np.ndarray, expected_returns: pd.Series, cov_matrix: pd.DataFrame) -> Tuple[float, float, float]:
        """Returns portfolio return, volatility, and Sharpe ratio."""
        returns = np.sum(expected_returns * weights)
        std_dev = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe = (returns - self.risk_free_rate) / std_dev if std_dev > 0 else 0
        return returns, std_dev, sharpe

    def _minimize_volatility(self, weights: np.ndarray, expected_returns: pd.Series, cov_matrix: pd.DataFrame) -> float:
        return self.portfolio_performance(weights, expected_returns, cov_matrix)[1]

    def _negative_sharpe(self, weights: np.ndarray, expected_returns: pd.Series, cov_matrix: pd.DataFrame) -> float:
        return -self.portfolio_performance(weights, expected_returns, cov_matrix)[2]

    def optimize_max_sharpe(self, expected_returns: pd.Series, cov_matrix: pd.DataFrame) -> Dict[str, Any]:
        """Optimizes portfolio weights to maximize Sharpe Ratio."""
        num_assets = len(expected_returns)
        args = (expected_returns, cov_matrix)
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(num_assets))
        initial_guess = num_assets * [1. / num_assets,]

        result = minimize(self._negative_sharpe, initial_guess, args=args,
                        method='SLSQP', bounds=bounds, constraints=constraints)
        
        opt_ret, opt_vol, opt_sharpe = self.portfolio_performance(result.x, expected_returns, cov_matrix)
        
        return {
            "weights": dict(zip(expected_returns.index, result.x)),
            "expected_return": opt_ret,
            "volatility": opt_vol,
            "sharpe_ratio": opt_sharpe
        }

    def optimize_min_variance(self, expected_returns: pd.Series, cov_matrix: pd.DataFrame) -> Dict[str, Any]:
        """Optimizes portfolio weights to minimize Volatility (Variance)."""
        num_assets = len(expected_returns)
        args = (expected_returns, cov_matrix)
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(num_assets))
        initial_guess = num_assets * [1. / num_assets,]

        result = minimize(self._minimize_volatility, initial_guess, args=args,
                        method='SLSQP', bounds=bounds, constraints=constraints)
        
        opt_ret, opt_vol, opt_sharpe = self.portfolio_performance(result.x, expected_returns, cov_matrix)
        
        return {
            "weights": dict(zip(expected_returns.index, result.x)),
            "expected_return": opt_ret,
            "volatility": opt_vol,
            "sharpe_ratio": opt_sharpe
        }


