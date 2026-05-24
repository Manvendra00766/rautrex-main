import pytest
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

def test_single_revenue_year_growth(dcf_service):
    """Single revenue year → CAGR defaults to 0 growth, no crash"""
    revenue = [300000]
    growth = dcf_service.calculate_revenue_growth(revenue)
    assert growth == 0.0

def test_revenue_zero_value(dcf_service, base_dcf_input):
    """Revenue list with a zero value → handles without ZeroDivisionError"""
    base_dcf_input.revenue = [0, 250000, 280000]
    # calculate_revenue_growth handles first <= 0
    output = dcf_service.calculate_intrinsic_value(base_dcf_input)
    assert output.intrinsic_value_per_share is not None

def test_ebit_margin_zero(dcf_service, base_dcf_input):
    """ebit_margin=0 → FCF is negative, intrinsic value still computes"""
    base_dcf_input.ebit_margin = 0.0
    output = dcf_service.calculate_intrinsic_value(base_dcf_input)
    assert output.intrinsic_value_per_share is not None
    # With 0 margin, FCF should be negative (due to capex and nwc)
    assert all(fcf < 0 for fcf in output.projected_fcfs)

def test_net_debt_greater_than_ev(dcf_service, base_dcf_input):
    """net_debt > enterprise_value → equity_value is 0 or negative, no crash"""
    # Force low EV
    base_dcf_input.revenue = [100, 110, 120]
    base_dcf_input.net_debt = 1000000 # Very high debt
    output = dcf_service.calculate_intrinsic_value(base_dcf_input)
    assert output.equity_value < 0
    assert output.intrinsic_value_per_share < 0

def test_projection_years_max(dcf_service, base_dcf_input):
    """projection_years=10 → projected_fcfs length exactly 10"""
    base_dcf_input.projection_years = 10
    output = dcf_service.calculate_intrinsic_value(base_dcf_input)
    assert len(output.projected_fcfs) == 10

def test_extremely_high_wacc(dcf_service, base_dcf_input):
    """Extremely high WACC (0.50) → intrinsic value low but > 0"""
    base_dcf_input.wacc = 0.50
    base_dcf_input.net_debt = 0 # Ensure positive value for WACC test
    output = dcf_service.calculate_intrinsic_value(base_dcf_input)
    assert output.intrinsic_value_per_share > 0
    
    # Compare with normal WACC
    base_dcf_input.wacc = 0.12
    normal_output = dcf_service.calculate_intrinsic_value(base_dcf_input)
    assert output.intrinsic_value_per_share < normal_output.intrinsic_value_per_share

def test_negative_terminal_growth(dcf_service, base_dcf_input):
    """terminal_growth_rate < 0 (shrinking company) → still computes correctly"""
    base_dcf_input.terminal_growth_rate = -0.02
    output = dcf_service.calculate_intrinsic_value(base_dcf_input)
    assert output.intrinsic_value_per_share > 0
