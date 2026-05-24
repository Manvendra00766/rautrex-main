import pytest
from unittest.mock import patch, MagicMock
from services.dcf_service import DCFService
from schemas.dcf_schema import DCFInput

@pytest.fixture
def base_dcf_input():
    return DCFInput(
        ticker="RELIANCE.NS",
        revenue=[220000, 250000, 280000],
        ebit_margin=0.18,
        tax_rate=0.25,
        capex_pct=0.08,
        nwc_change_pct=0.02,
        wacc=0.12,
        terminal_growth_rate=0.04,
        projection_years=5,
        shares_outstanding=6765,
        net_debt=95000
    )

@pytest.fixture
def dcf_service():
    return DCFService()

def test_cagr_calculation(dcf_service):
    """Verify CAGR calculation correct to 4 decimal places"""
    revenue = [220000, 250000, 280000]
    expected_cagr = (280000 / 220000) ** (1 / (3 - 1)) - 1
    assert dcf_service.calculate_revenue_growth(revenue) == pytest.approx(expected_cagr, rel=1e-4)

def test_fcf_formula(dcf_service):
    """Verify FCF formula: EBIT*(1-tax) + D&A(3%) - CapEx - ΔNWC"""
    revenue = 300000
    ebit_margin = 0.18
    tax_rate = 0.25
    capex_pct = 0.08
    nwc_change_pct = 0.02
    
    # Manual calculation
    ebit = revenue * ebit_margin
    tax_payment = ebit * tax_rate
    da = revenue * 0.03
    capex = revenue * capex_pct
    nwc_change = revenue * nwc_change_pct
    expected_fcf = (ebit - tax_payment) + da - capex - nwc_change
    
    assert dcf_service.calculate_fcf(revenue, ebit_margin, tax_rate, capex_pct, nwc_change_pct) == pytest.approx(expected_fcf, rel=1e-3)

def test_terminal_value_gordon_growth(dcf_service):
    """Verify Terminal value Gordon Growth formula manually"""
    last_fcf = 50000
    tgr = 0.04
    wacc = 0.12
    num_years = 5
    
    # TV at end of projection = last_fcf * (1+tgr) / (wacc - tgr)
    tv_at_end = (last_fcf * (1 + tgr)) / (wacc - tgr)
    # Discounted TV = tv_at_end / (1+wacc)^num_years
    expected_pv_tv = tv_at_end / ((1 + wacc) ** num_years)
    
    assert dcf_service.calculate_terminal_value(last_fcf, tgr, wacc, num_years) == pytest.approx(expected_pv_tv, rel=1e-3)

def test_intrinsic_value_positive(dcf_service, base_dcf_input):
    """Intrinsic value > 0 for valid input"""
    output = dcf_service.calculate_intrinsic_value(base_dcf_input)
    assert output.intrinsic_value_per_share > 0

def test_sensitivity_table_size(dcf_service, base_dcf_input):
    """Sensitivity table is exactly 5x5"""
    output = dcf_service.calculate_intrinsic_value(base_dcf_input)
    table = output.sensitivity_table
    assert len(table) == 5  # 5 WACC rows
    for wacc_key in table:
        assert len(table[wacc_key]) == 5  # 5 TGR columns

def test_sensitivity_table_monotonic_wacc(dcf_service, base_dcf_input):
    """Sensitivity table: higher WACC → lower intrinsic value (monotonic check)"""
    output = dcf_service.calculate_intrinsic_value(base_dcf_input)
    table = output.sensitivity_table
    # Sort WACC keys (they are strings like '10.0%')
    wacc_keys = sorted(table.keys(), key=lambda x: float(x.strip('%')))
    tgr_keys = list(table[wacc_keys[0]].keys())
    
    for tgr in tgr_keys:
        values = [table[wacc][tgr] for wacc in wacc_keys]
        # Higher WACC should mean lower value
        for i in range(len(values) - 1):
            if values[i] != 0 and values[i+1] != 0: # Skip the zero guards if any
                assert values[i] >= values[i+1]

def test_sensitivity_table_monotonic_tgr(dcf_service, base_dcf_input):
    """Sensitivity table: higher TGR → higher intrinsic value (monotonic check)"""
    output = dcf_service.calculate_intrinsic_value(base_dcf_input)
    table = output.sensitivity_table
    wacc_keys = list(table.keys())
    # Sort TGR keys
    tgr_keys = sorted(table[wacc_keys[0]].keys(), key=lambda x: float(x.strip('%')))
    
    for wacc in wacc_keys:
        values = [table[wacc][tgr] for tgr in tgr_keys]
        # Higher TGR should mean higher value
        for i in range(len(values) - 1):
            if values[i] != 0 and values[i+1] != 0:
                assert values[i] <= values[i+1]

def test_wacc_tgr_division_by_zero_guard(dcf_service):
    """wacc == terminal_growth_rate → raises ValueError (division by zero guard)"""
    # Note: Current implementation has a safety floor, but requirement asks for ValueError.
    # We will test for the ValueError as requested by the senior QA spec.
    # If it fails, it indicates the code needs fixing to match requirements.
    # However, to avoid immediate failure if I'm not supposed to change code, 
    # I'll check if it raises or handles it. 
    # BUT the prompt says "WRITE THESE TEST FILES" with these specs.
    with pytest.raises(ValueError, match="WACC must be greater than terminal growth rate"):
        dcf_service.calculate_terminal_value(50000, 0.04, 0.04, 5)

def test_projection_years_length(dcf_service, base_dcf_input):
    """projection_years=1 → projected_fcfs has length 1"""
    base_dcf_input.projection_years = 1
    output = dcf_service.calculate_intrinsic_value(base_dcf_input)
    assert len(output.projected_fcfs) == 1

def test_negative_net_debt_increases_value(dcf_service, base_dcf_input):
    """All negative net_debt (net cash) increases equity value correctly"""
    base_dcf_input.net_debt = 50000
    val_with_debt = dcf_service.calculate_intrinsic_value(base_dcf_input).equity_value
    
    base_dcf_input.net_debt = -50000
    val_with_cash = dcf_service.calculate_intrinsic_value(base_dcf_input).equity_value
    
    assert val_with_cash > val_with_debt

@patch("services.dcf_service.yf.Ticker")
def test_fetch_current_price_success(mock_ticker, dcf_service):
    """fetch_current_price: yfinance patched → returns float"""
    mock_stock = MagicMock()
    mock_stock.fast_info.get.return_value = 2500.5
    mock_ticker.return_value = mock_stock
    
    price = dcf_service.fetch_current_price("RELIANCE.NS")
    assert isinstance(price, float)
    assert price == 2500.5

@patch("services.dcf_service.yf.Ticker")
def test_fetch_current_price_failure(mock_ticker, dcf_service):
    """fetch_current_price: yfinance raises exception → returns None"""
    mock_ticker.side_effect = Exception("API Down")
    
    price = dcf_service.fetch_current_price("RELIANCE.NS")
    assert price is None

@patch("services.dcf_service.yf.Ticker")
def test_fetch_current_price_fallback_fast_info(mock_ticker, dcf_service):
    """Verify fast_info fallback is triggered when stock.info raises exception"""
    mock_stock = MagicMock()
    mock_stock.info.get.side_effect = Exception("Yahoo block")
    mock_stock.fast_info.get.return_value = 150.0
    mock_ticker.return_value = mock_stock

    price = dcf_service.fetch_current_price("TEST")
    assert price == 150.0
    mock_stock.fast_info.get.assert_called_once_with('lastPrice')

@patch("services.dcf_service.yf.Ticker")
def test_fetch_current_price_fallback_history(mock_ticker, dcf_service):
    """Verify history fallback is triggered when info and fast_info both raise exception"""
    mock_stock = MagicMock()
    mock_stock.info.get.side_effect = Exception("Yahoo block")
    mock_stock.fast_info.get.side_effect = Exception("FastInfo block")
    import pandas as pd
    mock_df = pd.DataFrame({"Close": [190.0, 200.0]})
    mock_stock.history.return_value = mock_df
    mock_ticker.return_value = mock_stock

    price = dcf_service.fetch_current_price("TEST")
    assert price == 200.0
    mock_stock.history.assert_called_once_with(period='2d')

@patch("services.dcf_service.yf.Ticker")
def test_fetch_current_price_all_fail(mock_ticker, dcf_service):
    """Verify None returned when all price-fetching attempts fail"""
    mock_stock = MagicMock()
    mock_stock.info.get.side_effect = Exception("Info block")
    mock_stock.fast_info.get.side_effect = Exception("FastInfo block")
    mock_stock.history.side_effect = Exception("History block")
    mock_ticker.return_value = mock_stock

    price = dcf_service.fetch_current_price("TEST")
    assert price is None

def test_calculate_intrinsic_value_aborts_on_price_none(dcf_service, base_dcf_input):
    """Verify ValueError is raised if price fetch returns None"""
    with patch.object(dcf_service, "fetch_current_price", return_value=None):
        with pytest.raises(ValueError) as excinfo:
            dcf_service.calculate_intrinsic_value(base_dcf_input)
        assert "Unable to fetch current price" in str(excinfo.value)
