import pytest
import pandas as pd
import numpy as np
from httpx import AsyncClient, ASGITransport
from main import app
from unittest.mock import patch, MagicMock
from auth import get_current_user, User
import time

# Mock user for authentication
async def mock_get_current_user():
    return User(id="test-user-uuid", email="test@example.com")

@pytest.fixture
def mock_yf_data():
    # Create 2 years of daily data (approx 504 trading days)
    dates = pd.date_range(start="2022-01-01", end="2023-12-31", freq="B")
    df = pd.DataFrame(index=dates)
    # Simulate some realistic price action: random walk
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.015, len(dates))
    price = 100 * (1 + returns).cumprod()
    df['Open'] = price * (1 - 0.001)
    df['High'] = price * (1 + 0.005)
    df['Low'] = price * (1 - 0.005)
    df['Close'] = price
    df['Adj Close'] = price
    df['Volume'] = 1000000
    return df

@pytest.mark.asyncio
async def test_comparison_runs_all_6_strategies(mock_yf_data):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.backtester_service.yf.download") as mock_download:
        # Mocking multi-ticker download
        mock_download.return_value = pd.concat([mock_yf_data, mock_yf_data], axis=1, keys=['AAPL', '^GSPC'])
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "ticker": "AAPL",
                "start_date": "2022-01-01",
                "end_date": "2023-12-31",
                "initial_capital": 10000,
                "strategies": [
                    {"name": "SMA", "type": "sma_crossover", "params": {"fast_period": 10, "slow_period": 30}},
                    {"name": "RSI", "type": "rsi_reversion", "params": {"rsi_period": 14, "oversold": 30, "overbought": 70}},
                    {"name": "MACD", "type": "macd", "params": {}},
                    {"name": "BB", "type": "bollinger", "params": {}},
                    {"name": "MOM", "type": "momentum", "params": {}}
                ]
            }
            response = await ac.post("/api/v1/compare/strategies", json=payload)
            
        assert response.status_code == 200
        data = response.json()
        
        # 5 user strategies + 1 Buy & Hold baseline
        assert len(data["metrics"]) == 6
        assert "Buy & Hold" in data["metrics"]
        assert all(name in data["metrics"] for name in ["SMA", "RSI", "MACD", "BB", "MOM"])

@pytest.mark.asyncio
async def test_comparison_same_data_for_all(mock_yf_data):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.backtester_service.yf.download") as mock_download:
        mock_download.return_value = pd.concat([mock_yf_data, mock_yf_data], axis=1, keys=['AAPL', '^GSPC'])
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "ticker": "AAPL",
                "start_date": "2022-01-01",
                "end_date": "2023-12-31",
                "strategies": [{"name": "SMA", "type": "sma_crossover"}]
            }
            response = await ac.post("/api/v1/compare/strategies", json=payload)
            
        data = response.json()
        chart_data = data["chart_data"]
        # Verify trade dates are within requested range
        first_date = chart_data[0]["time"]
        last_date = chart_data[-1]["time"]
        assert first_date >= "2022-01-01"
        assert last_date <= "2023-12-31"

@pytest.mark.asyncio
async def test_comparison_metrics_complete(mock_yf_data):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.backtester_service.yf.download") as mock_download:
        mock_download.return_value = pd.concat([mock_yf_data, mock_yf_data], axis=1, keys=['AAPL', '^GSPC'])
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "ticker": "AAPL",
                "start_date": "2022-01-01",
                "end_date": "2023-12-31",
                "strategies": [{"name": "SMA", "type": "sma_crossover"}]
            }
            response = await ac.post("/api/v1/compare/strategies", json=payload)
            
        data = response.json()
        strat_metrics = data["metrics"]["SMA"]
        
        required_metrics = [
            "total_return", "cagr", "sharpe_ratio", "sortino_ratio", 
            "max_drawdown", "win_rate", "profit_factor", "total_trades", "avg_holding_period"
        ]
        for metric in required_metrics:
            assert metric in strat_metrics

@pytest.mark.asyncio
async def test_winner_per_metric_declared(mock_yf_data):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.backtester_service.yf.download") as mock_download:
        mock_download.return_value = pd.concat([mock_yf_data, mock_yf_data], axis=1, keys=['AAPL', '^GSPC'])
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "ticker": "AAPL",
                "start_date": "2022-01-01",
                "end_date": "2023-12-31",
                "strategies": [{"name": "SMA", "type": "sma_crossover"}]
            }
            response = await ac.post("/api/v1/compare/strategies", json=payload)
            
        data = response.json()
        winners = data["winners"]
        
        # Router defines these 7 metrics to compare
        expected_winners = ["total_return", "cagr", "sharpe_ratio", "sortino_ratio", "max_drawdown", "win_rate", "profit_factor"]
        for metric in expected_winners:
            assert metric in winners
            assert winners[metric] is not None

@pytest.mark.asyncio
async def test_equity_curves_same_length(mock_yf_data):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.backtester_service.yf.download") as mock_download:
        mock_download.return_value = pd.concat([mock_yf_data, mock_yf_data], axis=1, keys=['AAPL', '^GSPC'])
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "ticker": "AAPL",
                "start_date": "2022-01-01",
                "end_date": "2023-12-31",
                "strategies": [
                    {"name": "SMA", "type": "sma_crossover"},
                    {"name": "RSI", "type": "rsi_reversion"}
                ]
            }
            response = await ac.post("/api/v1/compare/strategies", json=payload)
            
        data = response.json()
        chart_data = data["chart_data"]
        
        for pt in chart_data:
            assert "time" in pt
            assert "Buy & Hold" in pt
            assert "SMA" in pt
            assert "RSI" in pt

@pytest.mark.asyncio
async def test_equity_curves_start_same_value(mock_yf_data):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    initial_cap = 50000.0
    
    with patch("services.backtester_service.yf.download") as mock_download:
        mock_download.return_value = pd.concat([mock_yf_data, mock_yf_data], axis=1, keys=['AAPL', '^GSPC'])
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "ticker": "AAPL",
                "start_date": "2022-01-01",
                "end_date": "2023-12-31",
                "initial_capital": initial_cap,
                "strategies": [{"name": "SMA", "type": "sma_crossover"}]
            }
            response = await ac.post("/api/v1/compare/strategies", json=payload)
            
        data = response.json()
        first_pt = data["chart_data"][0]
        assert first_pt["SMA"] == initial_cap
        assert first_pt["Buy & Hold"] == initial_cap

@pytest.mark.asyncio
async def test_buy_hold_always_included(mock_yf_data):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.backtester_service.yf.download") as mock_download:
        mock_download.return_value = pd.concat([mock_yf_data, mock_yf_data], axis=1, keys=['AAPL', '^GSPC'])
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "ticker": "AAPL",
                "start_date": "2022-01-01",
                "end_date": "2023-12-31",
                "strategies": []
            }
            response = await ac.post("/api/v1/compare/strategies", json=payload)
            
        data = response.json()
        assert "Buy & Hold" in data["metrics"]
        assert len(data["metrics"]) == 1

@pytest.mark.asyncio
async def test_max_5_user_strategies(mock_yf_data):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "ticker": "AAPL",
            "start_date": "2022-01-01",
            "end_date": "2023-12-31",
            "strategies": [
                {"name": "S1", "type": "sma_crossover"},
                {"name": "S2", "type": "sma_crossover"},
                {"name": "S3", "type": "sma_crossover"},
                {"name": "S4", "type": "sma_crossover"},
                {"name": "S5", "type": "sma_crossover"},
                {"name": "S6", "type": "sma_crossover"}
            ]
        }
        response = await ac.post("/api/v1/compare/strategies", json=payload)
        
    # We expect 422 because we will add validation to the router
    assert response.status_code == 422
    assert "maximum 5 strategies allowed" in response.text.lower()

@pytest.mark.asyncio
async def test_identical_strategies_same_result(mock_yf_data):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.backtester_service.yf.download") as mock_download:
        mock_download.return_value = pd.concat([mock_yf_data, mock_yf_data], axis=1, keys=['AAPL', '^GSPC'])
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "ticker": "AAPL",
                "start_date": "2022-01-01",
                "end_date": "2023-12-31",
                "strategies": [
                    {"name": "SMA_1", "type": "sma_crossover", "params": {"fast_period": 50, "slow_period": 200}},
                    {"name": "SMA_2", "type": "sma_crossover", "params": {"fast_period": 50, "slow_period": 200}}
                ]
            }
            response = await ac.post("/api/v1/compare/strategies", json=payload)
            
        data = response.json()
        if "metrics" not in data:
            print(f"DEBUG: Response data: {data}")
        m1 = data["metrics"]["SMA_1"]
        m2 = data["metrics"]["SMA_2"]
        
        assert m1["total_return"] == m2["total_return"]
        assert m1["sharpe_ratio"] == m2["sharpe_ratio"]

@pytest.mark.asyncio
async def test_comparison_response_time(mock_yf_data):
    app.dependency_overrides[get_current_user] = mock_get_current_user
    
    with patch("services.backtester_service.yf.download") as mock_download:
        mock_download.return_value = pd.concat([mock_yf_data, mock_yf_data], axis=1, keys=['AAPL', '^GSPC'])
        
        start_time = time.time()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "ticker": "AAPL",
                "start_date": "2022-01-01",
                "end_date": "2023-12-31",
                "strategies": [
                    {"name": "S1", "type": "sma_crossover"},
                    {"name": "S2", "type": "rsi_reversion"},
                    {"name": "S3", "type": "macd"},
                    {"name": "S4", "type": "bollinger"},
                    {"name": "S5", "type": "momentum"}
                ]
            }
            response = await ac.post("/api/v1/compare/strategies", json=payload)
        
        end_time = time.time()
        assert response.status_code == 200
        assert (end_time - start_time) < 15.0
