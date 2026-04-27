import pytest
import pandas as pd
import numpy as np
from httpx import AsyncClient, ASGITransport
from main import app
from unittest.mock import patch, MagicMock
from auth import get_current_user, User

# Mock user for authentication
async def mock_get_current_user():
    return User(id="test-user-uuid", email="test@example.com")

@pytest.fixture
def mock_yf_price():
    # Mock prices for AAPL and MSFT as columns in a DataFrame
    df = pd.DataFrame({
        "AAPL": [150.0],
        "MSFT": [250.0]
    }, index=[pd.Timestamp("2023-01-01")])
    return df

@pytest.mark.asyncio
async def test_rebalance_shows_drift(mock_yf_price):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.portfolio_service.yf.download") as mock_download:
        mock_download.return_value = mock_yf_price
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "current_positions": [
                    {"ticker": "AAPL", "shares": 100}, # 15000
                    {"ticker": "MSFT", "shares": 100}  # 25000
                ], # Total = 40000. AAPL = 37.5%, MSFT = 62.5%
                "target_weights": {"AAPL": 0.5, "MSFT": 0.5},
                "threshold": 0.01
            }
            response = await ac.post("/api/v1/portfolio/rebalance", json=payload)
            
        if response.status_code != 200:
            print(f"DEBUG: Error response: {response.text}")
        assert response.status_code == 200
        data = response.json()
        # Drift = Current - Target
        # AAPL: 0.375 - 0.5 = -0.125
        # MSFT: 0.625 - 0.5 = 0.125
        assert data["drift"]["AAPL"] == -0.125
        assert data["drift"]["MSFT"] == 0.125

@pytest.mark.asyncio
async def test_trades_net_to_zero(mock_yf_price):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.portfolio_service.yf.download") as mock_download:
        mock_download.return_value = mock_yf_price
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "current_positions": [
                    {"ticker": "AAPL", "shares": 100},
                    {"ticker": "MSFT", "shares": 100}
                ],
                "target_weights": {"AAPL": 0.5, "MSFT": 0.5},
                "threshold": 0.01
            }
            response = await ac.post("/api/v1/portfolio/rebalance", json=payload)
            
        data = response.json()
        trades = data["trades"]
        # Sum of BUY (positive) and SELL (negative) should be zero
        net_val = 0
        for t in trades:
            if t["action"] == "BUY":
                net_val += t["amount"]
            else:
                net_val -= t["amount"]
        
        assert abs(net_val) < 0.01

@pytest.mark.asyncio
async def test_buy_when_underweight(mock_yf_price):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.portfolio_service.yf.download") as mock_download:
        mock_download.return_value = mock_yf_price
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "current_positions": [{"ticker": "AAPL", "shares": 10}], # Val=1500
                "target_weights": {"AAPL": 0.8, "MSFT": 0.2}, # MSFT is missing, must BUY
                "threshold": 0.01
            }
            response = await ac.post("/api/v1/portfolio/rebalance", json=payload)
            
        data = response.json()
        msft_trade = next(t for t in data["trades"] if t["ticker"] == "MSFT")
        assert msft_trade["action"] == "BUY"

@pytest.mark.asyncio
async def test_sell_when_overweight(mock_yf_price):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.portfolio_service.yf.download") as mock_download:
        mock_download.return_value = mock_yf_price
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "current_positions": [{"ticker": "AAPL", "shares": 100}], # 100% AAPL
                "target_weights": {"AAPL": 0.2, "MSFT": 0.8},
                "threshold": 0.01
            }
            response = await ac.post("/api/v1/portfolio/rebalance", json=payload)
            
        data = response.json()
        aapl_trade = next(t for t in data["trades"] if t["ticker"] == "AAPL")
        assert aapl_trade["action"] == "SELL"

@pytest.mark.asyncio
async def test_no_trade_within_threshold(mock_yf_price):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.portfolio_service.yf.download") as mock_download:
        mock_download.return_value = mock_yf_price
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # AAPL: 100 shares * 150 = 15000
            # MSFT: 60 shares * 250 = 15000
            # Total = 30000. Each is 50%.
            # Target is 50/50. Drift is 0. Threshold 10%.
            payload = {
                "current_positions": [{"ticker": "AAPL", "shares": 100}, {"ticker": "MSFT", "shares": 60}],
                "target_weights": {"AAPL": 0.5, "MSFT": 0.5},
                "threshold": 0.10
            }
            response = await ac.post("/api/v1/portfolio/rebalance", json=payload)
            
        data = response.json()
        assert len(data["trades"]) == 0

@pytest.mark.asyncio
async def test_trade_when_exceeds_threshold(mock_yf_price):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.portfolio_service.yf.download") as mock_download:
        mock_download.return_value = mock_yf_price
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # AAPL: 100 shares * 150 = 15000 (75%)
            # MSFT: 20 shares * 250 = 5000  (25%)
            # Total = 20000. 
            # Target 50/50. Drift is 25%. Threshold 5%.
            payload = {
                "current_positions": [{"ticker": "AAPL", "shares": 100}, {"ticker": "MSFT", "shares": 20}],
                "target_weights": {"AAPL": 0.5, "MSFT": 0.5},
                "threshold": 0.05
            }
            response = await ac.post("/api/v1/portfolio/rebalance", json=payload)
            
        data = response.json()
        assert len(data["trades"]) > 0

@pytest.mark.asyncio
async def test_estimated_cost_positive(mock_yf_price):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.portfolio_service.yf.download") as mock_download:
        mock_download.return_value = mock_yf_price
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "current_positions": [{"ticker": "AAPL", "shares": 100}],
                "target_weights": {"AAPL": 0.5, "MSFT": 0.5},
                "threshold": 0.01
            }
            response = await ac.post("/api/v1/portfolio/rebalance", json=payload)
            
        data = response.json()
        assert all(t["estimated_cost"] > 0 for t in data["trades"])
        assert data["total_estimated_cost"] > 0

@pytest.mark.asyncio
async def test_post_rebalance_weights_near_target(mock_yf_price):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.portfolio_service.yf.download") as mock_download:
        mock_download.return_value = mock_yf_price
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "current_positions": [{"ticker": "AAPL", "shares": 100}],
                "target_weights": {"AAPL": 0.5, "MSFT": 0.5},
                "threshold": 0.01
            }
            response = await ac.post("/api/v1/portfolio/rebalance", json=payload)
            
        data = response.json()
        # After trades, weights should be targets
        assert data["post_rebalance_weights"]["AAPL"] == 0.5
        assert data["post_rebalance_weights"]["MSFT"] == 0.5

@pytest.mark.asyncio
async def test_rebalance_backtest_annual():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    # Mock multiple years of data
    dates = pd.date_range(start="2020-01-01", end="2022-12-31", freq="D")
    df = pd.DataFrame(index=dates)
    df["AAPL"] = 150.0 + np.cumsum(np.random.normal(0, 1, len(dates)))
    df["MSFT"] = 250.0 + np.cumsum(np.random.normal(0, 1, len(dates)))
    
    with patch("services.portfolio_service.yf.download") as mock_download:
        mock_download.return_value = df
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "tickers": ["AAPL", "MSFT"],
                "target_weights": {"AAPL": 0.5, "MSFT": 0.5},
                "frequency": "annual",
                "start_date": "2020-01-01"
            }
            response = await ac.post("/api/v1/portfolio/rebalance/backtest", json=payload)
            
        if response.status_code != 200:
            print(f"DEBUG: Backtest error response: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert "annual_metrics" in data
        assert len(data["annual_metrics"]) >= 3
        # Check keys in first year
        first_year = data["annual_metrics"][0]
        assert "year" in first_year
        assert "rebalanced_return" in first_year
        assert "unrebalanced_return" in first_year
        assert "rebalancing_cost" in first_year

@pytest.mark.asyncio
async def test_rebalancing_cost_drag():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    # Mock data where prices don't change, but rebalancing happens
    dates = pd.date_range(start="2020-01-01", periods=13, freq="ME")
    df = pd.DataFrame(index=dates)
    # Volatile but zero drift to trigger rebalance costs
    df["AAPL"] = [100, 110, 90, 110, 90, 110, 90, 110, 90, 110, 90, 110, 100]
    df["MSFT"] = [100, 90, 110, 90, 110, 90, 110, 90, 110, 90, 110, 90, 100]
    
    with patch("services.portfolio_service.yf.download") as mock_download:
        mock_download.return_value = df
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "tickers": ["AAPL", "MSFT"],
                "target_weights": {"AAPL": 0.5, "MSFT": 0.5},
                "frequency": "monthly",
                "start_date": "2020-01-01"
            }
            response = await ac.post("/api/v1/portfolio/rebalance/backtest", json=payload)
            
        data = response.json()
        # Cumulative return should be lower for rebalanced due to costs
        # (Actually depend on the mock, but cost drag means it should lose to gross)
        assert data["total_rebalancing_costs"] > 0
        # Rebalanced total return should be lower than unrebalanced if they start/end at same prices but costs were paid
        assert data["rebalanced"]["total_return"] < data["no_rebalance"]["total_return"]
