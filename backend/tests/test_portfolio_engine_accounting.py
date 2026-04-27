from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.portfolio_engine import compute_portfolio_state
from services.pricing_engine import PriceSnapshot


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


def test_tsla_nvda_nav_and_pnl_are_consistent():
    transactions = [
        {
            "transaction_type": "DEPOSIT",
            "gross_amount": 1_000_000,
            "executed_at": "2026-01-01T00:00:00+00:00",
        },
        {
            "transaction_type": "BUY",
            "symbol": "TSLA",
            "quantity": 100,
            "price": 200,
            "fees": 0,
            "executed_at": "2026-01-02T00:00:00+00:00",
        },
        {
            "transaction_type": "BUY",
            "symbol": "NVDA",
            "quantity": 50,
            "price": 1000,
            "fees": 0,
            "executed_at": "2026-01-03T00:00:00+00:00",
        },
    ]
    prices = {
        "TSLA": make_snapshot("TSLA", last_price=220, previous_close=215),
        "NVDA": make_snapshot("NVDA", last_price=1100, previous_close=1090),
    }

    state = compute_portfolio_state(transactions, prices)
    positions = {position["ticker"]: position for position in state["positions"]}

    assert round(state["cash_balance"], 2) == 930000.00
    assert round(state["total_market_value"], 2) == 77000.00
    assert round(state["total_nav"], 2) == 1007000.00

    assert round(positions["TSLA"]["cost_basis"], 2) == 20000.00
    assert round(positions["TSLA"]["market_value"], 2) == 22000.00
    assert round(positions["TSLA"]["unrealized_pnl"], 2) == 2000.00

    assert round(positions["NVDA"]["cost_basis"], 2) == 50000.00
    assert round(positions["NVDA"]["market_value"], 2) == 55000.00
    assert round(positions["NVDA"]["unrealized_pnl"], 2) == 5000.00


def test_fifo_realized_pnl_uses_oldest_lot():
    transactions = [
        {"transaction_type": "DEPOSIT", "gross_amount": 100000, "executed_at": "2026-01-01T00:00:00+00:00"},
        {"transaction_type": "BUY", "symbol": "TSLA", "quantity": 10, "price": 100, "fees": 0, "executed_at": "2026-01-02T00:00:00+00:00"},
        {"transaction_type": "BUY", "symbol": "TSLA", "quantity": 10, "price": 120, "fees": 0, "executed_at": "2026-01-03T00:00:00+00:00"},
        {"transaction_type": "SELL", "symbol": "TSLA", "quantity": 10, "price": 150, "fees": 0, "lot_method": "FIFO", "executed_at": "2026-01-04T00:00:00+00:00"},
    ]
    prices = {"TSLA": make_snapshot("TSLA", last_price=150, previous_close=148)}

    state = compute_portfolio_state(transactions, prices)
    position = state["positions"][0]

    assert round(state["total_realized_pnl"], 2) == 500.00
    assert round(position["avg_cost_per_share"], 2) == 120.00
    assert round(position["cost_basis"], 2) == 1200.00


def test_lifo_realized_pnl_uses_newest_lot():
    transactions = [
        {"transaction_type": "DEPOSIT", "gross_amount": 100000, "executed_at": "2026-01-01T00:00:00+00:00"},
        {"transaction_type": "BUY", "symbol": "TSLA", "quantity": 10, "price": 100, "fees": 0, "executed_at": "2026-01-02T00:00:00+00:00"},
        {"transaction_type": "BUY", "symbol": "TSLA", "quantity": 10, "price": 120, "fees": 0, "executed_at": "2026-01-03T00:00:00+00:00"},
        {"transaction_type": "SELL", "symbol": "TSLA", "quantity": 10, "price": 150, "fees": 0, "lot_method": "LIFO", "executed_at": "2026-01-04T00:00:00+00:00"},
    ]
    prices = {"TSLA": make_snapshot("TSLA", last_price=150, previous_close=148)}

    state = compute_portfolio_state(transactions, prices)
    position = state["positions"][0]

    assert round(state["total_realized_pnl"], 2) == 300.00
    assert round(position["avg_cost_per_share"], 2) == 100.00
    assert round(position["cost_basis"], 2) == 1000.00
