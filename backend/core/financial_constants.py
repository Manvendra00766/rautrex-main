"""
RAUTREX Financial Constants — Single Source of Truth
All modules must import from here. Never hardcode financial rates inline.

Last updated: 2026-05-23 — 5.0%
"""

# Risk-free rate: annualized, used for Sharpe, Sortino, Black-Scholes, DCF WACC
# Source: Reflects the general 10-year US Treasury yield anchor.
RISK_FREE_RATE: float = 0.05  # 5.0%

# Trading periods per year (equity markets)
TRADING_DAYS_PER_YEAR: int = 252

# Default portfolio rebalancing frequency (days)
DEFAULT_REBALANCE_DAYS: int = 30
