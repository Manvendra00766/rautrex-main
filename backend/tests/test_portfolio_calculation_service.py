import pytest
import numpy as np
import pandas as pd
from services.portfolio_calculation_service import PortfolioCalculationService

def log_test_result(test_name: str, inputs: dict, expected: any, actual: any, status: str):
    print(f"\n--- TEST: {test_name} ({status}) ---")
    print(f"Input: {inputs}")
    print(f"Expected output: {expected}")
    print(f"Actual output: {actual}")
    print(f"Pass/fail: {status}")

def test_safe_div():
    test_name = "test_safe_div"
    inputs = {"numerator": 10, "denominator": 0}
    expected = 0.0
    actual = PortfolioCalculationService.safe_div(10, 0)
    status = "PASS" if actual == expected else "FAIL"
    log_test_result(test_name, inputs, expected, actual, status)
    assert actual == expected

def test_calculate_nav():
    test_name = "test_calculate_nav"
    cash = 10000.0
    positions = [
        {"shares": 10, "live_price": 150.0},
        {"shares": 5, "live_price": 300.0}
    ]
    inputs = {"cash": cash, "positions": positions}
    expected = 13000.0
    actual = PortfolioCalculationService.calculate_nav(cash, positions)
    status = "PASS" if actual == expected else "FAIL"
    log_test_result(test_name, inputs, expected, actual, status)
    assert actual == expected

def test_calculate_weights_sums_to_100():
    test_name = "test_calculate_weights_sums_to_100"
    positions = [
        {"shares": 10, "live_price": 150.0},
        {"shares": 5, "live_price": 300.0},
        {"shares": 1, "live_price": 75.0}
    ]
    inputs = {"positions": positions}
    res = PortfolioCalculationService.calculate_weights(positions)
    total_weight = sum(p["weight_pct"] for p in res)
    expected = 100.0
    actual = total_weight
    status = "PASS" if abs(actual - expected) < 1e-9 else "FAIL"
    log_test_result(test_name, inputs, expected, actual, status)
    assert abs(actual - expected) < 1e-9

def test_calculate_sharpe_ratio():
    test_name = "test_calculate_sharpe_ratio"
    # Create simple series of daily returns
    # standard deviation should be non-zero
    np.random.seed(42)
    returns = np.random.normal(0.0005, 0.01, 100) # mean ~ 0.05% daily, vol ~ 1% daily
    inputs = {"returns_sample_size": len(returns), "rf": 0.05, "periods": 252}
    
    # Calculate Sharpe manually for expected value
    s_returns = pd.Series(returns)
    vol_daily = s_returns.std()
    rf_daily = 0.05 / 252
    excess_returns = s_returns - rf_daily
    expected = (excess_returns.mean() / vol_daily) * np.sqrt(252)
    
    actual = PortfolioCalculationService.calculate_sharpe_ratio(returns, risk_free_rate=0.05, periods=252)
    status = "PASS" if pytest.approx(actual, 1e-6) == expected else "FAIL"
    log_test_result(test_name, inputs, expected, actual, status)
    assert pytest.approx(actual, 1e-6) == expected

def test_calculate_sortino_ratio_corrected_denominator():
    test_name = "test_calculate_sortino_ratio_corrected_denominator"
    returns = [0.01, -0.02, 0.015, -0.01, 0.005, -0.005] # N = 6
    inputs = {"returns": returns, "rf": 0.05, "periods": 252}
    
    rf_daily = 0.05 / 252
    excess_returns = np.array(returns) - rf_daily
    downside_returns = np.minimum(excess_returns, 0.0)
    # Corrected denominator: divide by N (6), not N_negative (3)
    downside_variance = np.sum(downside_returns ** 2) / len(returns)
    downside_dev = np.sqrt(downside_variance) * np.sqrt(252)
    expected = (excess_returns.mean() * 252) / downside_dev
    
    actual = PortfolioCalculationService.calculate_sortino_ratio(returns, risk_free_rate=0.05, periods=252)
    status = "PASS" if pytest.approx(actual, 1e-6) == expected else "FAIL"
    log_test_result(test_name, inputs, expected, actual, status)
    assert pytest.approx(actual, 1e-6) == expected

def test_calculate_historical_var():
    test_name = "test_calculate_historical_var"
    np.random.seed(42)
    returns = np.random.normal(0, 0.02, 1000)
    inputs = {"returns_sample_size": len(returns), "confidence_level": 0.95}
    expected = np.percentile(returns, 5) # 5th percentile for 95% confidence
    actual = PortfolioCalculationService.calculate_historical_var(returns, confidence_level=0.95)
    status = "PASS" if pytest.approx(actual, 1e-6) == expected else "FAIL"
    log_test_result(test_name, inputs, expected, actual, status)
    assert pytest.approx(actual, 1e-6) == expected

def test_calculate_max_drawdown():
    test_name = "test_calculate_max_drawdown"
    navs = pd.Series([100.0, 105.0, 95.0, 90.0, 110.0, 100.0])
    # Peak is 105.0, Trough is 90.0 -> Max drawdown = (90 - 105) / 105 = -15 / 105 = -0.142857
    inputs = {"nav_series": navs.tolist()}
    expected = -15.0 / 105.0
    actual = PortfolioCalculationService.calculate_max_drawdown(navs)
    status = "PASS" if pytest.approx(actual, 1e-6) == expected else "FAIL"
    log_test_result(test_name, inputs, expected, actual, status)
    assert pytest.approx(actual, 1e-6) == expected
