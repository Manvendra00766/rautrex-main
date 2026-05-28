import math
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd
from core.financial_constants import RISK_FREE_RATE

class PortfolioCalculationService:
    """
    PortfolioCalculationService serves as the Single Source of Truth (SSOT)
    for all financial and quantitative calculations across RAUTREX.
    
    Standardized Parameters:
    - Default Risk Free Rate (R_f) = 5.0% annualized (0.05)
    - Default Annualization Days = 252 trading days
    - Default VaR Confidence Level = 95%
    """

    @staticmethod
    def safe_div(numerator: float, denominator: float) -> float:
        """
        Safely divide two numbers, returning 0.0 if the denominator is zero or invalid.
        """
        try:
            num = float(numerator)
            den = float(denominator)
        except (ValueError, TypeError):
            return 0.0

        if den == 0.0 or math.isnan(den) or math.isinf(den):
            return 0.0
            
        if math.isnan(num) or math.isinf(num):
            return 0.0
            
        return num / den

    @classmethod
    def calculate_nav(cls, cash: float, positions: List[Dict[str, Any]]) -> float:
        """
        Calculate Net Asset Value (NAV) of the portfolio.
        NAV = Cash + sum of (shares * current_price) for all open positions.
        """
        total_market_value = sum(
            float(p.get("shares", 0)) * float(p.get("live_price", p.get("price", 0)))
            for p in positions
        )
        try:
            cash_val = float(cash) if cash is not None else 0.0
            if math.isnan(cash_val) or math.isinf(cash_val):
                cash_val = 0.0
        except (ValueError, TypeError):
            cash_val = 0.0
        return cash_val + total_market_value

    @classmethod
    def calculate_weights(cls, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculate portfolio weights ensuring they sum to exactly 100% if invested.
        This modifies positions in-place or returns them with 'weight_pct' populated.
        """
        total_market_value = sum(
            float(p.get("shares", 0)) * float(p.get("live_price", p.get("price", 0)))
            for p in positions
        )
        
        if total_market_value <= 0.0:
            for p in positions:
                p["weight_pct"] = 0.0
            return positions

        # Calculate preliminary weights
        for p in positions:
            mv = float(p.get("shares", 0)) * float(p.get("live_price", p.get("price", 0)))
            p["weight_pct"] = (mv / total_market_value) * 100.0

        # Adjust the largest weight to handle minor rounding differences so the sum is exactly 100.0
        current_sum = sum(p["weight_pct"] for p in positions)
        diff = 100.0 - current_sum
        if abs(diff) > 1e-9 and len(positions) > 0:
            # Find position with max market value to adjust
            max_pos = max(positions, key=lambda x: float(x.get("shares", 0)) * float(x.get("live_price", x.get("price", 0))))
            max_pos["weight_pct"] = float(max_pos["weight_pct"]) + diff

        return positions

    @classmethod
    def calculate_sharpe_ratio(
        cls,
        returns: Union[pd.Series, np.ndarray, List[float]],
        risk_free_rate: float = RISK_FREE_RATE,
        periods: int = 252
    ) -> float:
        """
        Unified Sharpe Ratio calculation.
        Formula:
          R_f_daily = risk_free_rate / periods
          excess_returns = daily_returns - R_f_daily
          Sharpe = (mean(excess_returns) / std(daily_returns)) * sqrt(periods)
        """
        if returns is None:
            return 0.0
            
        s_returns = pd.Series(returns) if not isinstance(returns, pd.Series) else returns
        s_returns = s_returns.replace([np.inf, -np.inf], np.nan).dropna()
        
        if len(s_returns) < 2:
            return 0.0

        vol_daily = float(s_returns.std())
        if vol_daily <= 0.0 or np.isnan(vol_daily):
            return 0.0

        # Unified daily risk-free rate
        rf_daily = risk_free_rate / periods
        excess_returns = s_returns - rf_daily
        mean_excess = float(excess_returns.mean())

        # Unified Sharpe formula
        sharpe = (mean_excess / vol_daily) * np.sqrt(periods)
        return float(sharpe) if not (np.isnan(sharpe) or np.isinf(sharpe)) else 0.0

    @classmethod
    def calculate_sortino_ratio(
        cls,
        returns: Union[pd.Series, np.ndarray, List[float]],
        risk_free_rate: float = RISK_FREE_RATE,
        periods: int = 252
    ) -> float:
        """
        Corrected Sortino Ratio calculation.
        The downside deviation denominator uses total sample size N of observations,
        not just the count of negative excess returns.
        
        Formula:
          R_f_daily = risk_free_rate / periods
          excess_returns = daily_returns - R_f_daily
          downside_returns = min(excess_returns, 0.0)
          downside_deviation = sqrt( sum(downside_returns^2) / N ) * sqrt(periods)
          Sortino = (mean(excess_returns) * periods) / downside_deviation
        """
        if returns is None:
            return 0.0

        s_returns = pd.Series(returns) if not isinstance(returns, pd.Series) else returns
        s_returns = s_returns.replace([np.inf, -np.inf], np.nan).dropna()
        
        N = len(s_returns)
        if N < 2:
            return 0.0

        rf_daily = risk_free_rate / periods
        excess_returns = s_returns - rf_daily
        mean_excess = float(excess_returns.mean())

        # Corrected downside deviation: compute sum of squared negative excess returns over total N observations
        downside_returns = np.minimum(excess_returns, 0.0)
        downside_variance = np.sum(downside_returns ** 2) / N
        downside_dev = np.sqrt(downside_variance) * np.sqrt(periods)

        if downside_dev <= 0.0 or np.isnan(downside_dev):
            return 0.0

        sortino = (mean_excess * periods) / downside_dev
        return float(sortino) if not (np.isnan(sortino) or np.isinf(sortino)) else 0.0

    @classmethod
    def calculate_historical_var(
        cls,
        returns: Union[pd.Series, np.ndarray, List[float]],
        confidence_level: float = 0.95
    ) -> float:
        """
        Standardized Historical Value at Risk (VaR) at 95% confidence level.
        Returns the percentile representation of returns (usually negative).
        """
        if returns is None:
            return 0.0

        s_returns = pd.Series(returns) if not isinstance(returns, pd.Series) else returns
        s_returns = s_returns.replace([np.inf, -np.inf], np.nan).dropna()

        if len(s_returns) < 2:
            return 0.0

        percentile = (1.0 - confidence_level) * 100.0
        var = float(np.percentile(s_returns, percentile))
        return var if not (np.isnan(var) or np.isinf(var)) else 0.0

    @classmethod
    def calculate_drawdowns(cls, nav_series: pd.Series) -> pd.Series:
        """
        Calculate drawdown series from a NAV series.
        Drawdown = (NAV / Peak_NAV) - 1.0
        """
        if nav_series is None or nav_series.empty:
            return pd.Series(dtype=float)
            
        running_max = nav_series.cummax()
        # Avoid division by zero
        with np.errstate(divide="ignore", invalid="ignore"):
            result = nav_series / running_max
        drawdowns = result.replace([np.inf, -np.inf], np.nan).fillna(1.0) - 1.0
        return drawdowns

    @classmethod
    def calculate_max_drawdown(cls, nav_series: pd.Series) -> float:
        """
        Calculate Maximum Drawdown of a NAV series.
        """
        drawdowns = cls.calculate_drawdowns(nav_series)
        if drawdowns.empty:
            return 0.0
        return float(drawdowns.min())

    @classmethod
    def calculate_daily_pnl(cls, positions: List[Dict[str, Any]]) -> float:
        """
        Calculate total daily P&L.
        daily_pnl = sum(shares * (live_price - previous_close))
        """
        return sum(
            float(p.get("shares", 0)) * (
                float(p.get("live_price", p.get("price", 0))) - 
                float(p.get("previous_close", p.get("live_price", p.get("price", 0))))
            )
            for p in positions
        )

    @classmethod
    def calculate_unrealized_pnl(cls, positions: List[Dict[str, Any]]) -> float:
        """
        Calculate total unrealized P&L.
        unrealized_pnl = sum(shares * (live_price - avg_cost_per_share))
        """
        return sum(
            float(p.get("shares", 0)) * (
                float(p.get("live_price", p.get("price", 0))) - 
                float(p.get("avg_cost_per_share", 0))
            )
            for p in positions
        )
