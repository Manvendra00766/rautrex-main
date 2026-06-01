from datetime import date
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services import pricing_engine
from services.market_data_policy import allow_yfinance_fallback, is_indian_market_symbol


def test_yfinance_fallback_disabled_by_default_in_production(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ALLOW_YFINANCE_FALLBACK", raising=False)

    assert allow_yfinance_fallback() is False


def test_yfinance_fallback_can_be_enabled_explicitly(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_YFINANCE_FALLBACK", "true")

    assert allow_yfinance_fallback() is True


def test_indian_symbol_detection_covers_equities_and_bonds():
    assert is_indian_market_symbol("RELIANCE.NS") is True
    assert is_indian_market_symbol("TCS.BO") is True
    assert is_indian_market_symbol("709GS2074.NS") is True
    assert is_indian_market_symbol("AAPL") is False


def test_quote_sync_does_not_touch_yfinance_when_disabled(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ALLOW_YFINANCE_FALLBACK", raising=False)

    with patch("services.pricing_engine.yf.Ticker", side_effect=AssertionError("yfinance should not be called")):
        assert pricing_engine._fetch_quote_sync("AAPL") is None


@pytest.mark.asyncio
async def test_history_does_not_touch_yfinance_when_disabled(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ALLOW_YFINANCE_FALLBACK", raising=False)

    with patch("services.pricing_engine.yf.download", side_effect=AssertionError("yfinance should not be called")):
        histories = await pricing_engine.get_price_history(["AAPL"], date(2026, 1, 1), date(2026, 1, 31))

    assert histories == {}
