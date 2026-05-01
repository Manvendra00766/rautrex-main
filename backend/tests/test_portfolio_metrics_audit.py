import pytest
from datetime import datetime, timezone, date
from services.portfolio_engine import compute_portfolio_state, build_equity_curve
from services.analytics_engine import compute_equity_metrics, summarize_allocation
from services.pricing_engine import PriceSnapshot
import pandas as pd

UTC = timezone.utc

def make_snapshot(symbol: str, last_price: float, previous_close: float) -> PriceSnapshot:
    return PriceSnapshot(
        symbol=symbol,
        name=symbol,
        asset_type="equity",
        currency="USD",
        exchange="NASDAQ",
        sector="Technology",
        country="US",
        market_cap=None,
        previous_close=previous_close,
        last_price=last_price,
        change_amount=last_price - previous_close,
        change_percent=((last_price - previous_close) / previous_close) * 100 if previous_close else 0.0,
        volume=1_000_000,
        source="test",
        fetched_at=datetime.now(tz=UTC),
        raw={},
    )

def test_weight_uses_holdings_market_value():
    # Setup: 1000 cash, 10 shares of AAPL at 100 (1000 market value)
    # Total NAV = 2000, Total Market Value = 1000
    # Weight should be 1000/1000 = 100%, NOT 1000/2000 = 50%
    transactions = [
        {"transaction_type": "DEPOSIT", "gross_amount": 2000, "executed_at": "2026-01-01T00:00:00Z"},
        {"transaction_type": "BUY", "symbol": "AAPL", "quantity": 10, "price": 100, "fees": 0, "executed_at": "2026-01-02T00:00:00Z"},
    ]
    prices = {"AAPL": make_snapshot("AAPL", 100, 100)}
    
    state = compute_portfolio_state(transactions, prices)
    position = state["positions"][0]
    
    assert position["ticker"] == "AAPL"
    assert position["weight_pct"] == 100.0
    assert state["cash_balance"] == 1000.0
    assert state["total_nav"] == 2000.0

def test_summarize_allocation_uses_holdings_market_value():
    positions = [
        {"ticker": "AAPL", "market_value": 1000, "sector": "Tech", "asset_type": "equity", "country": "US"}
    ]
    # Total Market Value = 1000. Even if NAV is 5000, Tech should be 100%
    res = summarize_allocation(positions, 1000)
    assert res["by_sector"][0]["label"] == "Tech"
    assert res["by_sector"][0]["weight_pct"] == 100.0

def test_twr_mtd_ytd_ignores_cash_flows():
    # Day 1: 100 NAV.
    # Day 2: Price same, but DEPOSIT 900. NAV=1000. Return should be 0%, not 900%.
    curve = [
        {"snapshot_date": "2026-01-01", "nav": 100, "daily_pnl": 0, "net_cash_flow": 100},
        {"snapshot_date": "2026-01-02", "nav": 1000, "daily_pnl": 0, "net_cash_flow": 900},
    ]
    metrics = compute_equity_metrics(curve)
    assert metrics["mtd_return_pct"] == 0.0
    assert metrics["ytd_return_pct"] == 0.0

def test_twr_calculates_correctly_with_price_changes():
    # Day 1: 100 NAV.
    # Day 2: Price up 10%. NAV=110. PnL=10. Return=10%.
    # Day 3: Deposit 890. NAV=1000. PnL=0. Return=0%.
    # Day 4: Price up 5%. NAV=1050. PnL=50. Return=5%.
    # Cumulative TWR: (1.1 * 1.05) - 1 = 15.5%
    curve = [
        {"snapshot_date": "2026-01-01", "nav": 100, "daily_pnl": 0, "net_cash_flow": 100},
        {"snapshot_date": "2026-01-02", "nav": 110, "daily_pnl": 10, "net_cash_flow": 0},
        {"snapshot_date": "2026-01-03", "nav": 1000, "daily_pnl": 0, "net_cash_flow": 890},
        {"snapshot_date": "2026-01-04", "nav": 1050, "daily_pnl": 50, "net_cash_flow": 0},
    ]
    metrics = compute_equity_metrics(curve)
    assert round(metrics["mtd_return_pct"], 2) == 15.5
    assert round(metrics["ytd_return_pct"], 2) == 15.5

def test_daily_pnl_in_curve_is_price_driven():
    # Setup: Buy 10 AAPL at 100 on Jan 1.
    # Jan 2: Price 110. daily_pnl should be 100.
    # Jan 3: Deposit 1000. daily_pnl should be 0.
    transactions = [
        {"transaction_type": "DEPOSIT", "gross_amount": 1000, "executed_at": "2026-01-01T00:00:00Z"},
        {"transaction_type": "BUY", "symbol": "AAPL", "quantity": 10, "price": 100, "fees": 0, "executed_at": "2026-01-01T00:01:00Z"},
        {"transaction_type": "DEPOSIT", "gross_amount": 1000, "executed_at": "2026-01-03T00:00:00Z"},
    ]
    price_history = {
        "AAPL": pd.Series({
            datetime(2026, 1, 1): 100,
            datetime(2026, 1, 2): 110,
            datetime(2026, 1, 3): 110,
        })
    }
    
    curve = build_equity_curve(transactions, price_history, date(2026, 1, 3))
    
    assert curve[0]["daily_pnl"] == 0
    assert curve[1]["daily_pnl"] == 100 # (110-100) * 10
    assert curve[2]["daily_pnl"] == 0
    assert curve[2]["net_cash_flow"] == 1000
