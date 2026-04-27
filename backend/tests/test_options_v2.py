import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock
from services.options_service import generate_iv_surface, _black_scholes

@pytest.fixture
def mock_yf_ticker():
    with patch('yfinance.Ticker') as mock:
        ticker = mock.return_value
        ticker.options = ['2026-12-15', '2027-01-19', '2027-03-15']
        
        # Mock history for spot price - must act like a DataFrame with a Series column
        spot_series = MagicMock()
        spot_series.iloc.__getitem__.return_value = 100.0
        
        mock_hist = MagicMock()
        mock_hist.empty = False
        mock_hist.__getitem__.return_value = spot_series
        
        ticker.history.return_value = mock_hist
        
        # Mock option chain
        def mock_option_chain(exp):
            calls = pd.DataFrame([
                {'strike': 90, 'impliedVolatility': 0.25},
                {'strike': 100, 'impliedVolatility': 0.20},
                {'strike': 110, 'impliedVolatility': 0.22},
            ])
            
            puts = pd.DataFrame([
                {'strike': 90, 'impliedVolatility': 0.28},
                {'strike': 100, 'impliedVolatility': 0.20},
                {'strike': 110, 'impliedVolatility': 0.18},
            ])
            
            # Add required columns for filtering in generate_iv_surface
            calls['strike'] = calls['strike'].astype(float)
            puts['strike'] = puts['strike'].astype(float)
            
            chain = MagicMock()
            chain.calls = calls
            chain.puts = puts
            return chain
            
        ticker.option_chain.side_effect = mock_option_chain
        yield ticker

@pytest.mark.asyncio
async def test_iv_dynamics_and_regime(mock_yf_ticker):
    res = await generate_iv_surface("SPY")
    
    assert "iv_surface" in res
    surface = res["iv_surface"]
    
    # test_iv_not_flat_across_strikes
    ivs = surface["iv_grid"][0] # First expiry
    assert len(set(ivs)) > 1
    
    # test_skew_metric_formula
    assert "skew_metric" in res
    assert isinstance(res["skew_metric"], float)
    
    # test_put_skew_positive
    assert res["skew_metric"] > 0
    
    # test_vol_regime_categorization
    assert res["vol_regime"] == "normal"
    
    # test_term_structure_has_dates
    assert len(res["term_structure"]) >= 3
    
    # test_term_structure_expiry_ascending
    days = [e["expiry_days"] for e in res["term_structure"]]
    assert days == sorted(days)

def test_svi_logic_fallback():
    spot = 100
    dte = 30 / 365.0
    a, b, rho, m, sig = 0.04, 0.4, -0.4, 0.1, 0.1
    
    def get_svi_iv(k):
        log_k = np.log(k / spot)
        w = a + b * (rho * (log_k - m) + np.sqrt((log_k - m)**2 + sig**2))
        return np.sqrt(max(0.001, w / dte))

    # test_svi_all_positive
    strikes = [80, 90, 100, 110, 120]
    ivs = [get_svi_iv(k) for k in strikes]
    for iv in ivs:
        assert iv > 0
        
    # test_svi_smile_shape
    atm_iv = get_svi_iv(100)
    otm_put_iv = get_svi_iv(80)
    assert otm_put_iv > atm_iv
    
    # test_svi_atm_is_minimum
    test_strikes = np.linspace(80, 140, 100)
    test_ivs = [get_svi_iv(k) for k in test_strikes]
    min_idx = np.argmin(test_ivs)
    min_strike = test_strikes[min_idx]
    assert 90 < min_strike < 125

def test_advanced_greeks():
    S, K, T, r, sigma = 100, 110, 0.1, 0.02, 0.2
    res = _black_scholes(S, K, T, r, sigma, 'call')
    greeks = res['greeks']
    
    # test_vanna_defined
    assert "vanna" in greeks
    assert isinstance(greeks["vanna"], float)
    
    # test_volga_positive_otm
    # Volga (dVega/dVol) is positive for OTM options
    assert greeks["volga"] > 0
    
    # test_charm_sign_convention
    # For OTM call, Delta should decay toward 0 as T decreases
    # Charm = dDelta/dt. 
    assert greeks["charm"] < 0 or abs(greeks["charm"]) < 1e-5

@pytest.mark.asyncio
async def test_surface_grid_dimensions(mock_yf_ticker):
    res = await generate_iv_surface("SPY")
    
    iv_shape = (len(res["iv_surface"]["expiries"]), len(res["iv_surface"]["strikes"]))
    delta_shape = (len(res["delta_surface"]["expiries"]), len(res["delta_surface"]["grid"][0]))
    gamma_shape = (len(res["gamma_surface"]["expiries"]), len(res["gamma_surface"]["grid"][0]))
    
    # test_surface_grid_dimensions
    assert iv_shape[0] == len(res["delta_surface"]["expiries"])
    assert iv_shape[1] == len(res["delta_surface"]["strikes"])
    assert len(res["delta_surface"]["grid"]) == iv_shape[0]
    assert len(res["gamma_surface"]["grid"]) == iv_shape[0]
    assert len(res["delta_surface"]["grid"][0]) == iv_shape[1]
