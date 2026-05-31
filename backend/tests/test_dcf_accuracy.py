import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from services.dcf_service import dcf_service
from schemas.dcf_schema import DCFInput

@pytest.mark.asyncio
async def test_aapl_financials():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/stocks/AAPL")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ticker"] == "AAPL"
    assert data["currency"] == "USD"
    assert data["unit"] == "Mn"
    
    # Assert revenue > $350,000 Mn (TTM ~$391 Bn)
    assert len(data["revenue"]) >= 2
    assert data["revenue"][-1] > 350000
    
    # Assert EBIT margin between 25% and 40%
    assert 0.25 <= data["ebit_margin"] <= 0.40
    
    # Assert tax rate between 10% and 30% (Apple is generally low)
    assert 0.10 <= data["tax_rate"] <= 0.30
    
    # Assert shares outstanding between 14,000 Mn and 17,000 Mn
    assert 14000 <= data["shares_outstanding"] <= 17000
    
    # Assert net debt is populated correctly (Apple sometimes has net cash, sometimes slight net debt depending on cash vs debt exact figures)
    assert data["net_debt"] is not None

@pytest.mark.asyncio
async def test_reliance_financials():

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/stocks/RELIANCE.NS")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["ticker"] == "RELIANCE.NS"
    assert data["currency"] == "INR"
    assert data["unit"] == "Cr"
    
    # Assert revenue > 800,000 Cr
    assert len(data["revenue"]) >= 2
    assert data["revenue"][-1] > 800000

def test_fcf_calculation():
    # Mock inputs
    rev = 100.0
    ebit_margin = 0.20
    tax = 0.25
    capex_pct = 0.10
    da_pct = 0.05
    nwc_pct = 0.03
    
    # FCF = EBIT * (1 - tax) - CapEx + D&A - NWC
    # FCF = (100 * 0.20) * 0.75 - (100 * 0.10) + (100 * 0.05) - (100 * 0.03)
    # FCF = 20 * 0.75 - 10 + 5 - 3 = 15 - 10 + 5 - 3 = 7.0
    
    fcf = dcf_service.calculate_fcf(rev, ebit_margin, tax, capex_pct, da_pct, nwc_pct, 1)
    
    assert abs(fcf - 7.0) < 0.1

def test_wacc_tgr_guard():
    input_data = DCFInput(
        ticker="TEST",
        revenue=[100, 110],
        ebit_margin=0.20,
        tax_rate=0.25,
        capex_pct=0.10,
        da_pct=0.05,
        nwc_change_pct=0.03,
        wacc=0.03, # WACC <= TGR
        terminal_growth_rate=0.04,
        shares_outstanding=10,
        net_debt=0
    )
    
    import pytest
    with pytest.raises(ValueError) as excinfo:
        dcf_service.calculate_intrinsic_value(input_data)
    
    assert "WACC" in str(excinfo.value)
    assert "exceed Terminal Growth Rate" in str(excinfo.value)

def test_negative_fcf_handling():
    input_data = DCFInput(
        ticker="TEST",
        revenue=[100, 110],
        ebit_margin=-0.10, # Negative margin ensures negative FCF
        tax_rate=0.0,
        capex_pct=0.20, # High capex
        da_pct=0.05,
        nwc_change_pct=0.05,
        wacc=0.10,
        terminal_growth_rate=0.02,
        shares_outstanding=10,
        net_debt=0
    )
    
    output = dcf_service.calculate_intrinsic_value(input_data)
    
    # Assert all FCFs negative
    assert all(f < 0 for f in output.projected_fcfs)
    
    # Assert intrinsic value is actually negative, not 0
    assert output.intrinsic_value_per_share < 0
    
    # Assert warning is present
    assert any("Negative FCF" in w for w in output.warnings)
