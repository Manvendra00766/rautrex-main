import numpy as np
import pandas as pd
from typing import Tuple
from scipy.stats import norm

class RiskEngine:
    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level

    def historical_var(self, returns: pd.Series) -> float:
        """Calculate Historical Value at Risk (VaR)."""
        if returns.empty: return 0.0
        return np.percentile(returns, (1 - self.confidence_level) * 100)

    def parametric_var(self, returns: pd.Series) -> float:
        """Calculate Parametric (Variance-Covariance) Value at Risk (VaR)."""
        if returns.empty: return 0.0
        mean = np.mean(returns)
        std_dev = np.std(returns)
        return norm.ppf(1 - self.confidence_level, mean, std_dev)

    def cvar(self, returns: pd.Series) -> float:
        """Calculate Conditional Value at Risk (CVaR) or Expected Shortfall."""
        if returns.empty: return 0.0
        var = self.historical_var(returns)
        cvar = returns[returns <= var].mean()
        return cvar if not np.isnan(cvar) else var

    def maximum_drawdown(self, prices: pd.Series) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
        """Calculate Maximum Drawdown and return (max_dd, peak_date, trough_date)."""
        if prices.empty: return 0.0, None, None
        rolling_max = prices.cummax()
        drawdown = prices / rolling_max - 1.0
        max_drawdown = drawdown.min()
        
        # Find the dates
        trough_date = drawdown.idxmin()
        # Find the peak before the trough
        peak_date = prices.loc[:trough_date].idxmax() if pd.notna(trough_date) else None
        
        return max_drawdown, peak_date, trough_date

    def stress_test(self, returns: pd.Series, shock_pct: float = -0.20) -> float:
        """Simulate portfolio return under a specific market shock."""
        # Simple beta-adjusted stress test or direct drop
        return returns.mean() + shock_pct
