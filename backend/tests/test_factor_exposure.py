import pytest
import pandas as pd
import numpy as np
from httpx import AsyncClient, ASGITransport
from main import app
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_yf_data():
    # 1 year of daily data (252 trading days)
    dates = pd.date_range(start="2023-01-01", periods=252, freq="B")
    tickers = ["AAPL", "SPY", "IWM", "VTV", "VUG", "QUAL", "SPLV", "MTUM"]
    
    np.random.seed(42)
    data = {}
    for t in tickers:
        # Create random returns with some correlations
        # SPY as base
        if t == "SPY":
            rets = np.random.normal(0.0005, 0.01, 252)
        else:
            # 0.7 correlation with SPY
            spy_rets = np.random.normal(0.0005, 0.01, 252) # will use actual SPY rets below
            idiosyncratic = np.random.normal(0, 0.005, 252)
            # Re-generate to ensure exact length and seed consistency if needed
            # but let's just use a simple linear combo for the mock
            rets = 0.7 * np.random.normal(0.0005, 0.01, 252) + 0.3 * idiosyncratic
            
        price = 100 * (1 + rets).cumprod()
        data[t] = price
        
    df = pd.DataFrame(data, index=dates)
    return df

@pytest.mark.asyncio
async def test_3_factor_regression(mock_yf_data):
    with patch("services.risk_service.yf.download") as mock_download:
        mock_download.return_value = {"Close": mock_yf_data}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "portfolio": [{"ticker": "AAPL", "weight": 1.0}],
                "factors": 3,
                "momentum": False
            }
            response = await ac.post("/api/v1/risk/factors", json=payload)
            
        assert response.status_code == 200
        data = response.json()
        
        assert "alpha" in data
        assert "Market" in data["betas"]
        assert "Size" in data["betas"]
        assert "Value" in data["betas"]
        assert "r_squared" in data
        # Should NOT have Quality, Investment, Momentum
        assert "Quality" not in data["betas"]
        assert "Momentum" not in data["betas"]

@pytest.mark.asyncio
async def test_5_factor_all_present(mock_yf_data):
    with patch("services.risk_service.yf.download") as mock_download:
        mock_download.return_value = {"Close": mock_yf_data}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "portfolio": [{"ticker": "AAPL", "weight": 1.0}],
                "factors": 5,
                "momentum": False
            }
            response = await ac.post("/api/v1/risk/factors", json=payload)
            
        data = response.json()
        assert "Quality" in data["betas"]
        assert "Investment" in data["betas"]
        assert "Market" in data["betas"]
        assert "Size" in data["betas"]
        assert "Value" in data["betas"]

@pytest.mark.asyncio
async def test_r_squared_range(mock_yf_data):
    with patch("services.risk_service.yf.download") as mock_download:
        mock_download.return_value = {"Close": mock_yf_data}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "portfolio": [{"ticker": "AAPL", "weight": 1.0}]
            }
            response = await ac.post("/api/v1/risk/factors", json=payload)
            
        data = response.json()
        assert 0 <= data["r_squared"] <= 1.0

@pytest.mark.asyncio
async def test_market_beta_equity(mock_yf_data):
    with patch("services.risk_service.yf.download") as mock_download:
        mock_download.return_value = {"Close": mock_yf_data}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "portfolio": [{"ticker": "AAPL", "weight": 1.0}]
            }
            response = await ac.post("/api/v1/risk/factors", json=payload)
            
        data = response.json()
        market_beta = data["betas"]["Market"]
        assert -0.5 <= market_beta <= 3.0

@pytest.mark.asyncio
async def test_factor_contributions_sum_to_return(mock_yf_data):
    with patch("services.risk_service.yf.download") as mock_download:
        mock_download.return_value = {"Close": mock_yf_data}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "portfolio": [{"ticker": "AAPL", "weight": 1.0}]
            }
            response = await ac.post("/api/v1/risk/factors", json=payload)
            
        data = response.json()
        alpha_daily = data["alpha"] / 252
        attribution_sum = sum(data["attribution"].values())
        
        # Portfolio return (annualized)
        aapl_ret = mock_yf_data["AAPL"].pct_change().dropna().mean() * 252
        
        # In OLS: Port_Ret = Alpha + sum(Beta_i * Factor_Ret_i)
        # alpha in response is already annualized
        total_explained = data["alpha"] + attribution_sum
        
        assert abs(total_explained - aapl_ret) < 0.01

@pytest.mark.asyncio
async def test_rolling_betas_length(mock_yf_data):
    with patch("services.risk_service.yf.download") as mock_download:
        mock_download.return_value = {"Close": mock_yf_data}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "portfolio": [{"ticker": "AAPL", "weight": 1.0}],
                "start_date": "2023-01-01"
            }
            response = await ac.post("/api/v1/risk/factors", json=payload)
            
        data = response.json()
        # 252 prices -> 251 returns.
        # Window 63.
        # Length = 251 - 63 + 1 = 189.
        assert len(data["rolling_beta"]) == 189

@pytest.mark.asyncio
async def test_rolling_betas_vary(mock_yf_data):
    # To ensure they vary, let's inject a regime change in the mock data
    modified_data = mock_yf_data.copy()
    # First half: high correlation with SPY
    # Second half: negative correlation
    spy_rets = mock_yf_data["SPY"].pct_change().dropna()
    new_aapl_rets = []
    for i, ret in enumerate(spy_rets):
        if i < 120:
            new_aapl_rets.append(ret * 2.0 + np.random.normal(0, 0.001))
        else:
            new_aapl_rets.append(ret * -1.0 + np.random.normal(0, 0.001))
            
    # Series with correct index
    aapl_rets_series = pd.Series(new_aapl_rets, index=spy_rets.index)
    # Reconstruct prices starting from 100
    aapl_prices = 100 * (1 + aapl_rets_series).cumprod()
    # Prepend the initial price (100) for the first date
    first_date = modified_data.index[0]
    final_aapl = pd.Series([100.0], index=[first_date])._append(aapl_prices)
    
    modified_data["AAPL"] = final_aapl
    
    with patch("services.risk_service.yf.download") as mock_download:
        mock_download.return_value = {"Close": modified_data}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            payload = {
                "portfolio": [{"ticker": "AAPL", "weight": 1.0}]
            }
            response = await ac.post("/api/v1/risk/factors", json=payload)
            
        data = response.json()
        betas = [pt["beta"] for pt in data["rolling_beta"]]
        assert len(betas) > 0
        assert max(betas) != min(betas)
        # With 2.0 and -1.0 factors, we should see wide range
        assert any(b > 1.2 for b in betas)
        assert any(b < 0.0 for b in betas)

@pytest.mark.asyncio
async def test_momentum_factor_present(mock_yf_data):
    with patch("services.risk_service.yf.download") as mock_download:
        mock_download.return_value = {"Close": mock_yf_data}
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # Case 1: Included
            payload = {
                "portfolio": [{"ticker": "AAPL", "weight": 1.0}],
                "momentum": True
            }
            resp1 = await ac.post("/api/v1/risk/factors", json=payload)
            assert "Momentum" in resp1.json()["betas"]
            
            # Case 2: Excluded
            payload["momentum"] = False
            resp2 = await ac.post("/api/v1/risk/factors", json=payload)
            assert "Momentum" not in resp2.json()["betas"]
