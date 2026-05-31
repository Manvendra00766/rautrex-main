import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from auth import get_current_user
from routers.onboarding import get_dynamic_mvo_allocation

# --- 1. MOCK PRICE DATA GENERATION UTILITY ---

def generate_mock_historical_prices() -> pd.DataFrame:
    """
    Generates 252 days of daily close prices for the three Indian ETF proxies:
    NIFTYBEES.NS (equity), GOLDBEES.NS (gold), and LIQUIDBEES.NS (debt)
    with realistic returns and volatilities.
    """
    np.random.seed(42)
    days = 252
    
    # Equity: upward trend, moderate volatility
    eq_returns = np.random.normal(0.0005, 0.01, days)
    eq_prices = 100 * np.cumprod(1 + eq_returns)
    
    # Gold: safe asset, low correlation to equity, mild trend
    gold_returns = np.random.normal(0.0002, 0.008, days)
    gold_prices = 100 * np.cumprod(1 + gold_returns)
    
    # Debt: stable asset, extremely low volatility, steady interest
    debt_returns = np.random.normal(0.0001, 0.001, days)
    debt_prices = 100 * np.cumprod(1 + debt_returns)
    
    dates = pd.date_range(start="2023-01-01", periods=days, freq="B")
    
    df = pd.DataFrame({
        "equity": eq_prices,
        "gold": gold_prices,
        "debt": debt_prices
    }, index=dates)
    
    return df

# --- 2. FASTAPI MOCK AUTHENTICATION ENVIRONMENT ---

class MockUser:
    id = "00000000-0000-0000-0000-000000000789"
    email = "mvo_trader@rautrex.com"

def override_get_current_user():
    return MockUser()

app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)

# --- 3. HARDCORE TEST CASES ---

@pytest.mark.asyncio
@patch("routers.onboarding.yf.download")
async def test_dynamic_mvo_conservative_strategy(mock_download):
    """
    Test 1: Verifies that a Conservative profile successfully minimizes volatility 
    using the SLSQP solver, allocating heavily to debt and restricting equity/gold bounds.
    """
    mock_df = generate_mock_historical_prices()
    # Mock yfinance return value
    mock_download.return_value = mock_df
    
    # Execute Conservative allocation optimization
    weights = await get_dynamic_mvo_allocation(profile="Conservative", horizon="3-7 years")
    
    assert "equity" in weights
    assert "debt" in weights
    assert "gold" in weights
    
    # Sum of weights must equal 1.0 (100% allocation)
    assert pytest.approx(sum(weights.values()), rel=1e-2) == 1.0
    
    # Check that conservative boundaries are respected (Debt must hold majority)
    assert weights["debt"] >= 0.45
    assert weights["equity"] <= 0.40
    assert weights["gold"] <= 0.20


@pytest.mark.asyncio
@patch("routers.onboarding.yf.download")
async def test_dynamic_mvo_aggressive_strategy(mock_download):
    """
    Test 2: Verifies that an Aggressive profile successfully maximizes the Sharpe ratio
    using the SLSQP solver, allocating heavily to equity to capture maximum market return.
    """
    mock_df = generate_mock_historical_prices()
    mock_download.return_value = mock_df
    
    weights = await get_dynamic_mvo_allocation(profile="Aggressive", horizon="7_years_plus")
    
    assert pytest.approx(sum(weights.values()), rel=1e-2) == 1.0
    
    # Aggressive allocations must favor equities (min 65% up to 95% due to long horizon push)
    assert weights["equity"] >= 0.65
    assert weights["debt"] <= 0.25
    assert weights["gold"] <= 0.20


@pytest.mark.asyncio
@patch("routers.onboarding.yf.download")
async def test_dynamic_mvo_fallback_on_api_error(mock_download):
    """
    Test 3: Verifies that when the yfinance API raises a network error or returns 
    empty data, the engine catches it and falls back cleanly to static weights.
    """
    # Force yfinance download to raise a TimeoutError
    mock_download.side_effect = TimeoutError("Yahoo Finance Server Down")
    
    # Execute onboarding calculations
    weights = await get_dynamic_mvo_allocation(profile="Moderate", horizon="1-3 years")
    
    # Check that it successfully resolved to standard fallback Moderate weights
    assert weights == {"equity": 0.50, "debt": 0.30, "gold": 0.20}


def test_onboarding_new_investor_api_integration():
    """
    Test 4: Integration test mocking a new investor signup request to the `/api/v1/onboarding/new` POST route.
    Verifies that the database saves the portfolio and the resulting allocations sum exactly to the INR monthly amount.
    """
    # Mock yfinance inside the actual router during integration test execution
    with patch("routers.onboarding.yf.download") as mock_download:
        mock_download.return_value = generate_mock_historical_prices()
        
        onboarding_payload = {
            "goal": "Grow my money over time",
            "target": "Buying a home",
            "horizon": "7+ years",
            "monthly_amount": "₹15,000+", # Standard string input format from frontend
            "risk_reaction": "Stay calm, it will recover",
            "risk_tolerance": "No, I want growth",
            "knowledge_level": "I know the basics"
        }
        
        response = client.post(
            "/api/v1/onboarding/new",
            json=onboarding_payload,
            headers={"Authorization": "Bearer mock_token"}
        )
        
        assert response.status_code == 200
        res_data = response.json()
        
        assert "portfolio_suggestion" in res_data
        suggestion = res_data["portfolio_suggestion"]
        
        # Monthly amount ₹15,000+ should normalize to ₹20,000 budget
        assert suggestion["total"] == 20000
        
        allocations = suggestion["allocations"]
        assert len(allocations) > 0
        
        # Verify that all allocations sum exactly to the ₹20,000 rupee budget
        allocated_total = sum(item["amount"] for item in allocations)
        assert allocated_total == 20000
        
        # Ensure example mutual funds and buying portals exist in the response
        assert "example_fund" in allocations[0]
        assert "where_to_buy" in allocations[0]
