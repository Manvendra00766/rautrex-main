import pytest
import json
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from main import app
from dependencies import get_current_user

# Mock data for yfinance info
MOCK_INFO = {
    "longName": "Test Company",
    "currentPrice": 1000.0,
    "trailingPE": 15.0,
    "returnOnEquity": 0.2,
    "marketCap": 100000000000,
    "trailingEps": 50.0,
    "earningsGrowth": 0.15
}

@pytest.fixture
def mock_yf_ticker():
    with patch("yfinance.Ticker") as mock:
        ticker_instance = MagicMock()
        ticker_instance.info = MOCK_INFO
        # Mock history for RSI (need at least 15 days)
        dates = pd.date_range(start="2024-01-01", periods=30)
        hist_df = pd.DataFrame({
            "Close": np.linspace(900, 1000, 30)
        }, index=dates)
        ticker_instance.history.return_value = hist_df
        mock.return_value = ticker_instance
        yield mock

@pytest.fixture
def mock_redis():
    with patch("infrastructure.redis_client.redis_client.get", new_callable=AsyncMock) as mock_get, \
         patch("infrastructure.redis_client.redis_client.set", new_callable=AsyncMock) as mock_set:
        mock_get.return_value = None
        yield {"get": mock_get, "set": mock_set}

@pytest.fixture(autouse=True)
def override_auth():
    user = MagicMock()
    user.id = "test-user-id"
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides = {}

@pytest.mark.asyncio
async def test_screener_no_filters(mock_yf_ticker, mock_redis):
    """Test 1: Empty filters return top 20 stocks with all fields"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/screener/filter", json={})
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 20
    
    required_fields = {
        "symbol", "current_price", "pe_ratio", "roe", 
        "rsi", "market_cap", "dcf_margin_of_safety", "signal"
    }
    for stock in data:
        assert required_fields.issubset(stock.keys())

@pytest.mark.asyncio
async def test_screener_with_valid_filters(mock_yf_ticker, mock_redis):
    """Test 2: Stocks satisfy filter conditions"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        filters = {"min_pe": 5, "max_pe": 20, "min_roe": 0.1}
        response = await ac.post("/api/v1/screener/filter", json=filters)
    
    assert response.status_code == 200
    for stock in response.json():
        assert 5 <= stock["pe_ratio"] <= 20
        assert stock["roe"] >= 0.1

@pytest.mark.asyncio
async def test_screener_invalid_filter_values():
    """Test 3: Invalid values return 422"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/v1/screener/filter", json={"min_pe": -1})
    
    # If the schema doesn't have ge=0, this might pass 200. 
    # Requirement asks for 422.
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_screener_redis_cache_hit(mock_yf_ticker, mock_redis):
    """Test 4: Cache populates and hits"""
    filters = {"min_pe": 10}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # First call: Cache miss
        await ac.post("/api/v1/screener/filter", json=filters)
        assert mock_redis["set"].called
        
        # Prepare mock for cache hit
        cached_data = json.dumps([{
            "symbol": "REL.NS", "company_name": "R", "signal": "HOLD", 
            "current_price": 100, "pe_ratio": 15, "roe": 0.2, "rsi": 50, 
            "market_cap": 1000, "dcf_margin_of_safety": 10
        }])
        mock_redis["get"].return_value = cached_data
        
        # Second call: Cache hit
        response = await ac.post("/api/v1/screener/filter", json=filters)
        assert response.status_code == 200
        assert mock_redis["get"].call_count >= 2

@pytest.mark.asyncio
async def test_screener_yfinance_failure():
    """Test 5: 503 on yfinance failure"""
    with patch("services.screener_service.screener_service.get_stock_data") as mock_get:
        mock_get.side_effect = Exception("YF API Down")
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.post("/api/v1/screener/filter", json={})
        
        assert response.status_code == 503

@pytest.mark.asyncio
async def test_screener_signal_logic(mock_redis):
    """Test 6: BUY and AVOID signal logic"""
    from services.screener_service import screener_service
    
    # BUY: dcf_margin > 20 and rsi < 40
    with patch("yfinance.Ticker") as mock_yf:
        ticker = MagicMock()
        ticker.info = {
            "currentPrice": 100.0, "trailingPE": 10.0, "returnOnEquity": 0.2, 
            "marketCap": 1000000, "trailingEps": 10.0, "earningsGrowth": 0.15,
            "longName": "BuyCo"
        }
        ticker.history.return_value = pd.DataFrame({"Close": [100]*30}, index=pd.date_range("2024-01-01", periods=30))
        mock_yf.return_value = ticker
        
        with patch.object(screener_service, "calculate_rsi", return_value=30.0):
            res = await screener_service.get_stock_data("BUY.NS")
            assert res["signal"] == "BUY"

        # AVOID: rsi > 70
        with patch.object(screener_service, "calculate_rsi", return_value=75.0):
            res = await screener_service.get_stock_data("AVOID.NS")
            assert res["signal"] == "AVOID"
