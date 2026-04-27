import pytest
import pandas as pd
import numpy as np
from httpx import AsyncClient, ASGITransport
from main import app
from unittest.mock import patch, MagicMock
from datetime import datetime

@pytest.fixture
def mock_gfc_data():
    # Sep 2008 to Mar 2009
    dates = pd.date_range(start="2008-09-01", end="2009-03-01", freq="B")
    # Simulate a crash: prices drop by 40%
    np.random.seed(42)
    n = len(dates)
    trend = np.linspace(1, 0.6, n)
    noise = np.random.normal(0, 0.02, n)
    prices = 100 * trend * (1 + noise).cumprod()
    
    df = pd.DataFrame({"AAPL": prices, "SPY": prices * 0.95}, index=dates)
    return df

@pytest.mark.asyncio
async def test_10_scenarios_returned():
    # Use simple mock for any yf download
    with patch("services.risk_service.yf.download") as mock_download:
        # Just need some data to not fail
        dates = pd.date_range(start="2023-01-01", periods=10)
        mock_download.return_value = {"Close": pd.DataFrame({"AAPL": [100]*10, "SPY": [100]*10}, index=dates)}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {"portfolio": [{"ticker": "AAPL", "weight": 1.0}]}
            response = await ac.post("/api/v1/risk/scenarios", json=payload)
            
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10
        
        hist_count = len([s for s in data if s["type"] == "Historical"])
        hypo_count = len([s for s in data if s["type"] == "Hypothetical"])
        assert hist_count == 5
        assert hypo_count == 5

@pytest.mark.asyncio
async def test_historical_scenario_uses_real_data(mock_gfc_data):
    def side_effect(tickers, start, end):
        if start == "2008-09-01":
            return {"Close": mock_gfc_data}
        # Fallback for others
        dates = pd.date_range(start=start, end=end, freq="B")[:5]
        return {"Close": pd.DataFrame({t: [100]*len(dates) for t in tickers}, index=dates)}

    with patch("services.risk_service.yf.download", side_effect=side_effect):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {"portfolio": [{"ticker": "AAPL", "weight": 1.0}]}
            response = await ac.post("/api/v1/risk/scenarios", json=payload)
            
        data = response.json()
        gfc = next(s for s in data if s["name"] == "2008 GFC")
        # In mock_gfc_data, price goes from ~100 down to ~60 (approx -40%)
        assert -0.6 < gfc["your_portfolio_impact"] < -0.2

@pytest.mark.asyncio
async def test_hypothetical_shock_applied():
    # Mock beta data where one ticker has high beta, one has low
    dates = pd.date_range(start="2023-01-01", periods=100, freq="B")
    spy_rets = np.random.normal(0.0005, 0.01, 100)
    # T1: beta = 2.0
    t1_rets = spy_rets * 2.0 + np.random.normal(0, 0.001, 100)
    # T2: beta = 0.2
    t2_rets = spy_rets * 0.2 + np.random.normal(0, 0.001, 100)
    
    mock_df = pd.DataFrame({
        "SPY": 100 * (1 + spy_rets).cumprod(),
        "T1": 100 * (1 + t1_rets).cumprod(),
        "T2": 100 * (1 + t2_rets).cumprod()
    }, index=dates)

    with patch("services.risk_service.yf.download") as mock_download:
        mock_download.return_value = {"Close": mock_df}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # High beta portfolio
            resp_high = await ac.post("/api/v1/risk/scenarios", json={
                "portfolio": [{"ticker": "T1", "weight": 1.0}]
            })
            # Low beta portfolio
            resp_low = await ac.post("/api/v1/risk/scenarios", json={
                "portfolio": [{"ticker": "T2", "weight": 1.0}]
            })
            
        rate_high = next(s for s in resp_high.json() if s["name"] == "Rates +300bps")
        rate_low = next(s for s in resp_low.json() if s["name"] == "Rates +300bps")
        
        # High beta (tech/growth) should be hit harder by rate hike (negative impact)
        # So more negative = smaller number
        assert rate_high["your_portfolio_impact"] < rate_low["your_portfolio_impact"]

@pytest.mark.asyncio
async def test_scenario_impact_in_range():
    with patch("services.risk_service.yf.download") as mock_download:
        dates = pd.date_range(start="2023-01-01", periods=10)
        mock_download.return_value = {"Close": pd.DataFrame({"AAPL": [100]*10, "SPY": [100]*10}, index=dates)}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/risk/scenarios", json={
                "portfolio": [{"ticker": "AAPL", "weight": 1.0}]
            })
            
        data = response.json()
        for s in data:
            assert -1.0 <= s["your_portfolio_impact"] <= 0.5

@pytest.mark.asyncio
async def test_worst_day_within_scenario_period():
    with patch("services.risk_service.yf.download") as mock_download:
        # Use GFC dates
        start, end = "2008-09-01", "2009-03-01"
        dates = pd.date_range(start=start, end=end, freq="B")
        df = pd.DataFrame({"AAPL": [100]*len(dates), "SPY": [100]*len(dates)}, index=dates)
        # Make one day really bad
        df.iloc[10] = df.iloc[10] * 0.5
        mock_download.return_value = {"Close": df}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/risk/scenarios", json={
                "portfolio": [{"ticker": "AAPL", "weight": 1.0}]
            })
            
        data = response.json()
        gfc = next(s for s in data if s["name"] == "2008 GFC")
        
        assert start <= gfc["worst_day_date"] <= end

@pytest.mark.asyncio
async def test_most_affected_positions_present():
    with patch("services.risk_service.yf.download") as mock_download:
        dates = pd.date_range(start="2023-01-01", periods=10)
        mock_download.return_value = {"Close": pd.DataFrame({"AAPL": [100]*10, "SPY": [100]*10}, index=dates)}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/risk/scenarios", json={
                "portfolio": [{"ticker": "AAPL", "weight": 1.0}]
            })
            
        data = response.json()
        for s in data:
            assert "most_affected_positions" in s
            assert len(s["most_affected_positions"]) >= 1
            assert "ticker" in s["most_affected_positions"][0]
            assert "impact" in s["most_affected_positions"][0]

@pytest.mark.asyncio
async def test_portfolio_vs_benchmark_both_present():
    with patch("services.risk_service.yf.download") as mock_download:
        dates = pd.date_range(start="2023-01-01", periods=10)
        mock_download.return_value = {"Close": pd.DataFrame({"AAPL": [100]*10, "SPY": [100]*10}, index=dates)}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/risk/scenarios", json={
                "portfolio": [{"ticker": "AAPL", "weight": 1.0}]
            })
            
        data = response.json()
        for s in data:
            assert "your_portfolio_impact" in s
            assert "benchmark_impact" in s

@pytest.mark.asyncio
async def test_crash_scenario_correlation_spike():
    with patch("services.risk_service.yf.download") as mock_download:
        dates = pd.date_range(start="2023-01-01", periods=10)
        mock_download.return_value = {"Close": pd.DataFrame({"AAPL": [100]*10, "SPY": [100]*10}, index=dates)}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post("/api/v1/risk/scenarios", json={
                "portfolio": [{"ticker": "AAPL", "weight": 1.0}]
            })
            
        data = response.json()
        crash = next(s for s in data if s["name"] == "Market Crash -30%")
        
        assert "correlations" in crash
        assert crash["correlations"]["avg_correlation"] >= 0.85
        assert crash["correlations"]["is_spike"] is True
