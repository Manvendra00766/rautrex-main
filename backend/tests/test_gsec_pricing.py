from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from services.portfolio_service import optimize_portfolio_logic
from services.pricing_engine import get_price_history, get_price_snapshot


@pytest.mark.asyncio
async def test_gsec_quote_does_not_call_yfinance():
    with (
        patch("services.pricing_engine.get_cached_price", new=AsyncMock(return_value=None)),
        patch("services.pricing_engine.bond_service.fetch_gsec_yields", new=AsyncMock(return_value={"yields": {"10Y": 7.1}})),
        patch("services.pricing_engine.yf.Ticker") as mock_ticker,
        patch("services.pricing_engine.yf.download") as mock_download,
    ):
        snapshot = await get_price_snapshot("709GS2074.NS")

    assert snapshot is not None
    assert snapshot.asset_type == "bond"
    assert snapshot.source == "FBIL"
    mock_ticker.assert_not_called()
    mock_download.assert_not_called()


@pytest.mark.asyncio
async def test_gsec_history_does_not_call_yfinance():
    with (
        patch("services.pricing_engine.get_active_upstox_token", new=AsyncMock(return_value=None)),
        patch("services.pricing_engine.yf.download") as mock_download,
    ):
        histories = await get_price_history(["709GS2074.NS"], date(2024, 1, 1), date(2024, 2, 1))

    assert histories == {}
    mock_download.assert_not_called()


@pytest.mark.asyncio
async def test_optimizer_handles_gsec_without_error():
    result = await optimize_portfolio_logic(["TMPV.NS", "709GS2074.NS"])

    assert "optimal_weights" in result
    assert "709GS2074.NS" in result["optimal_weights"]
    assert result["metrics"]["volatility"] >= 0
