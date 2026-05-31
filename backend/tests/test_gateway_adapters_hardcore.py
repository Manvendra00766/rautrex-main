import pytest
import httpx
import respx
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime

from services.market_data_service import market_data_service
from services.adapters.alpaca_adapter import AlpacaAdapter
from services.adapters.upstox_adapter import UpstoxAdapter
from services.adapters.oanda_adapter import OandaAdapter

# ── Mock Helper for yfinance ──────────────────────────────────────────
class MockYfinanceTicker:
    def __init__(self, symbol):
        self.symbol = symbol
        self.info = {
            "longName": f"Mock Corp {symbol}",
            "shortName": f"MC {symbol}",
            "currency": "INR" if symbol.endswith(".NS") or symbol.endswith(".BO") else "USD",
            "exchange": "NSE" if symbol.endswith(".NS") else "NASDAQ",
            "sector": "Technology",
            "country": "IN" if symbol.endswith(".NS") else "US",
            "marketCap": 1500000000,
            "previousClose": 100.0,
        }

    def history(self, period="5d", auto_adjust=False):
        # Return a simple mock DataFrame with Close and Volume
        dates = pd.date_range(end=datetime.now(), periods=5)
        df = pd.DataFrame(
            {
                "Open": [98.0, 99.0, 97.5, 101.0, 102.5],
                "High": [100.0, 101.5, 99.0, 103.0, 104.0],
                "Low": [97.0, 98.0, 96.5, 100.0, 101.0],
                "Close": [99.0, 98.0, 100.0, 102.0, 103.5],
                "Volume": [1000, 1500, 1200, 2000, 1800]
            },
            index=dates
        )
        return df

@pytest.fixture
def mock_yfinance():
    with patch("services.adapters.alpaca_adapter.yf.Ticker", side_effect=MockYfinanceTicker) as mock_alpaca_yf, \
         patch("services.adapters.upstox_adapter.yf.Ticker", side_effect=MockYfinanceTicker) as mock_upstox_yf, \
         patch("services.adapters.oanda_adapter.yf.Ticker", side_effect=MockYfinanceTicker) as mock_oanda_yf:
        yield {
            "alpaca": mock_alpaca_yf,
            "upstox": mock_upstox_yf,
            "oanda": mock_oanda_yf,
        }

# ════════════════════════════════════════════════════════════════════════
# HARDCORE TEST CASES
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_hardcore_routing_edge_cases():
    """Stress test the gateway routing logic with malformed, extreme, or mixed-case inputs."""
    # Whitespace and weird casings should strip and route properly
    assert isinstance(market_data_service._get_adapter("  aApL   "), AlpacaAdapter)
    assert isinstance(market_data_service._get_adapter("iNfY.Ns  "), UpstoxAdapter)
    assert isinstance(market_data_service._get_adapter("  gC=F  "), OandaAdapter)
    
    # Extreme length and symbols that don't match any rules should default safely to Alpaca
    assert isinstance(market_data_service._get_adapter("EXTREMELYLONGTICKERWITHSPECIALCHARS%$#@"), AlpacaAdapter)
    assert isinstance(market_data_service._get_adapter(""), AlpacaAdapter)
    assert isinstance(market_data_service._get_adapter("   "), AlpacaAdapter)


@pytest.mark.asyncio
async def test_hardcore_unconfigured_adapters(mock_yfinance):
    """Verify that adapters bypass remote calls and invoke the fallback instantly if config keys are empty."""
    alpaca = AlpacaAdapter()
    alpaca.api_key_id = ""
    alpaca.secret_key = ""
    assert not alpaca._is_configured()
    
    # Verify price fetch successfully falls back to yfinance mock
    res = await alpaca.fetch_price("MSFT")
    assert res is not None
    assert "fallback" in res.source.lower()
    assert res.last_price == 103.5
    assert res.previous_close == 102.0

    oanda = OandaAdapter()
    oanda.api_key = ""
    oanda.account_id = ""
    assert not oanda._is_configured()
    
    res_comm = await oanda.fetch_price("GC=F")
    assert res_comm is not None
    assert "fallback" in res_comm.source.lower()
    
    # Quote padded keys should strip and resolve configured state correctly in __init__
    from core.config import settings
    with patch.object(settings, "ALPACA_API_KEY_ID", '""'), \
         patch.object(settings, "ALPACA_SECRET_KEY", '""'):
        alpaca_padded = AlpacaAdapter()
        assert not alpaca_padded._is_configured()


@respx.mock
@pytest.mark.asyncio
async def test_hardcore_alpaca_http_errors_and_fallbacks(mock_yfinance):
    """Inject 401, 429, 500 errors and timeouts into Alpaca Client to ensure safe fallbacks."""
    alpaca = AlpacaAdapter()
    alpaca.api_key_id = "mock_key"
    alpaca.secret_key = "mock_secret"
    alpaca.base_url = "https://data.alpaca.markets/v2"
    assert alpaca._is_configured()

    # Route 1: 401 Unauthorized API Response
    respx.get("https://data.alpaca.markets/v2/stocks/snapshots").mock(
        return_value=httpx.Response(401, text="Unauthorized")
    )
    res = await alpaca.fetch_price("AAPL")
    assert res is not None
    assert "fallback" in res.source.lower()  # Fell back cleanly

    # Route 2: 429 Rate Limit Response
    respx.get("https://data.alpaca.markets/v2/stocks/snapshots").mock(
        return_value=httpx.Response(429, text="Rate Limited")
    )
    res = await alpaca.fetch_price("NVDA")
    assert res is not None
    assert "fallback" in res.source.lower()

    # Route 3: 500 Internal Server Error Response
    respx.get("https://data.alpaca.markets/v2/stocks/snapshots").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )
    res = await alpaca.fetch_price("AMD")
    assert res is not None
    assert "fallback" in res.source.lower()

    # Route 4: Request Timeout (Network Error)
    respx.get("https://data.alpaca.markets/v2/stocks/snapshots").mock(
        side_effect=httpx.ConnectTimeout("Connection timed out")
    )
    res = await alpaca.fetch_price("TSLA")
    assert res is not None
    assert "fallback" in res.source.lower()


@respx.mock
@pytest.mark.asyncio
async def test_hardcore_oanda_http_errors_and_fallbacks(mock_yfinance):
    """Inject 401, 429, 500 errors and timeouts into OANDA Client to ensure safe fallbacks."""
    oanda = OandaAdapter()
    oanda.api_key = "mock_oanda_key"
    oanda.account_id = "mock_account"
    oanda.base_url = "https://api-fxtrade.oanda.com"
    assert oanda._is_configured()

    url = f"{oanda.base_url}/v3/accounts/{oanda.account_id}/pricing"

    # Route 1: 401 Unauthorized
    respx.get(url).mock(return_value=httpx.Response(401, text="Unauthorized"))
    res = await oanda.fetch_price("GC=F")
    assert res is not None
    assert "fallback" in res.source.lower()

    # Route 2: 429 Rate limit
    respx.get(url).mock(return_value=httpx.Response(429, text="Rate Limit"))
    res = await oanda.fetch_price("CL=F")
    assert res is not None
    assert "fallback" in res.source.lower()

    # Route 3: 500 Internal Server Error
    respx.get(url).mock(return_value=httpx.Response(500, text="Server Error"))
    res = await oanda.fetch_price("SI=F")
    assert res is not None
    assert "fallback" in res.source.lower()

    # Route 4: Connection Timeout Exception
    respx.get(url).mock(side_effect=httpx.ConnectTimeout("Connect Timeout"))
    res = await oanda.fetch_price("NG=F")
    assert res is not None
    assert "fallback" in res.source.lower()


@pytest.mark.asyncio
async def test_hardcore_batch_fetch_error_isolation(mock_yfinance):
    """Verify fetch_batch isolates failures, guaranteeing that a crashed ticker does not contaminate others."""
    alpaca = AlpacaAdapter()
    alpaca.api_key_id = "" # Force fallback for simplicity & deterministic mock outputs
    
    # We patch fetch_price to throw an exception for a specific ticker to simulate failure isolation
    original_fetch = alpaca.fetch_price
    
    async def mock_fetch_price(symbol):
        if symbol == "CRASH_ME":
            raise RuntimeError("Fatal Exception simulated for ticker")
        return await original_fetch(symbol)
        
    alpaca.fetch_price = mock_fetch_price
    
    # Fetch batch containing valid and bad symbols
    batch_symbols = ["AAPL", "CRASH_ME", "MSFT"]
    res = await alpaca.fetch_batch(batch_symbols)
    
    assert len(res) == 3
    assert res["AAPL"] is not None
    assert res["AAPL"].symbol == "AAPL"
    assert res["AAPL"].last_price == 103.5
    
    assert res["MSFT"] is not None
    assert res["MSFT"].symbol == "MSFT"
    
    # The crashed ticker should return None but NOT raise exception out of fetch_batch
    assert res["CRASH_ME"] is None


@pytest.mark.asyncio
async def test_hardcore_historical_data_edge_cases(mock_yfinance):
    """Verify fetch_history handles invalid ticker configurations, empty records, and exceptions gracefully."""
    alpaca = AlpacaAdapter()
    
    # Invalid ticker returns empty list rather than crashing
    records = await alpaca.fetch_history("INVALID_SYMBOL", period="1mo")
    assert isinstance(records, list)
    
    # Simulate yfinance raising exception on historical fetch
    with patch("services.adapters.alpaca_adapter.yf.Ticker") as mock_yf:
        mock_instance = MagicMock()
        mock_instance.history.side_effect = Exception("General network collapse")
        mock_yf.return_value = mock_instance
        
        res_history = await alpaca.fetch_history("AAPL", period="1mo")
        assert res_history == []  # Gracefully swallowed and returned empty list


@pytest.mark.asyncio
async def test_hardcore_circuit_breaker_trips_on_fallback(mock_yfinance):
    """Verify that using a yfinance fallback properly increments the circuit breaker failure count and trips it."""
    from services.market_data_service import MarketDataService, CircuitState
    
    # We initialize a separate instance of MarketDataService to avoid dirtying the global singleton state
    service = MarketDataService()
    
    # Verify starting state is CLOSED
    assert service.circuit_breaker.state == CircuitState.CLOSED
    assert service.circuit_breaker.failure_count == 0
    
    # Force Alpaca adapter to be unconfigured so it ALWAYS uses yfinance fallback (returning is_fallback=True)
    service.alpaca_adapter.api_key_id = ""
    service.alpaca_adapter.secret_key = ""
    
    # Let's perform 5 sequential fetches for a US stock. Each should successfully fall back
    # but increment the failure count because is_fallback is True!
    for _ in range(5):
        res = await service.fetch_price("MSFT")
        assert res is not None
        assert res["source"] == "Alpaca (yfinance fallback)"
        
    # The circuit breaker should now be OPEN!
    assert service.circuit_breaker.state == CircuitState.OPEN
    assert service.circuit_breaker.failure_count == 5
    
    # Clean up and shutdown resources
    await service.close()
