import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app
from dependencies import get_current_user
import asyncio

client = TestClient(app)

# Mock user
class MockUser:
    def __init__(self, id):
        self.id = id

@pytest.fixture
def mock_user():
    return MockUser(id="test-user-uuid")

@pytest.fixture
def base_payload():
    return {
        "ticker": "RELIANCE.NS",
        "revenue": [220000, 250000, 280000],
        "ebit_margin": 0.18,
        "tax_rate": 0.25,
        "capex_pct": 0.08,
        "nwc_change_pct": 0.02,
        "wacc": 0.12,
        "terminal_growth_rate": 0.04,
        "projection_years": 5,
        "shares_outstanding": 6765,
        "net_debt": 95000
    }

def override_get_current_user():
    return MockUser(id="test-user-uuid")

app.dependency_overrides[get_current_user] = override_get_current_user

@patch("services.dcf_service.yf.Ticker")
def test_calculate_success(mock_ticker, base_payload):
    """POST /calculate with valid payload → 200, intrinsic_value_per_share > 0"""
    mock_stock = MagicMock()
    mock_stock.fast_info.get.return_value = 2500.0
    mock_ticker.return_value = mock_stock
    
    response = client.post("/api/v1/dcf/calculate", json=base_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intrinsic_value_per_share"] > 0
    assert data["ticker"] == "RELIANCE.NS"

def test_calculate_missing_field(base_payload):
    """POST /calculate missing field → 422"""
    del base_payload["ticker"]
    response = client.post("/api/v1/dcf/calculate", json=base_payload)
    assert response.status_code == 422

def test_calculate_wacc_tgr_error(base_payload):
    """POST /calculate wacc=terminal_growth_rate → 400"""
    base_payload["wacc"] = 0.04
    base_payload["terminal_growth_rate"] = 0.04
    # This expects the service to raise an exception that the router catches
    response = client.post("/api/v1/dcf/calculate", json=base_payload)
    assert response.status_code == 400

@patch("services.dcf_service.yf.Ticker")
@patch("routers.dcf_router.asyncio.gather", wraps=asyncio.gather)
def test_compare_success(mock_gather, mock_ticker, base_payload):
    """POST /compare valid payload → 200, winner is one of tickers or equal"""
    mock_stock = MagicMock()
    mock_stock.fast_info.get.return_value = 2500.0
    mock_ticker.return_value = mock_stock
    
    payload = {
        "input_a": base_payload,
        "input_b": {**base_payload, "ticker": "TCS.NS"}
    }
    
    response = client.post("/api/v1/dcf/compare", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["winner"] in ["RELIANCE.NS", "TCS.NS", "equal"]
    assert "upside_difference_pct" in data
    
    # Verify concurrent execution (asyncio.gather called)
    # Note: Depending on implementation, gather might be called internally or in router.
    # The router explicitly calls asyncio.gather.
    assert mock_gather.called

@patch("supabase_client.supabase.table")
def test_get_history(mock_table):
    """GET /history → 200, returns list (mock returns 2 rows)"""
    mock_response = MagicMock()
    mock_response.execute.return_value.data = [
        {"id": "1", "ticker": "RELIANCE.NS"},
        {"id": "2", "ticker": "TCS.NS"}
    ]
    mock_table.return_value.select.return_value.eq.return_value.order.return_value.execute = mock_response.execute
    
    response = client.get("/api/v1/dcf/history")
    assert response.status_code == 200
    assert len(response.json()) == 2

@patch("supabase_client.supabase.table")
def test_save_dcf(mock_table, base_payload):
    """POST /save → 201"""
    # First calculate to get output
    with patch("services.dcf_service.yf.Ticker") as mock_ticker:
        mock_stock = MagicMock()
        mock_stock.fast_info.get.return_value = 2500.0
        mock_ticker.return_value = mock_stock
        calc_response = client.post("/api/v1/dcf/calculate", json=base_payload)
        output_data = calc_response.json()

    save_payload = {
        "dcf_input": base_payload,
        "dcf_output": output_data
    }
    
    mock_response = MagicMock()
    mock_response.data = [{"id": "new-id"}]
    mock_table.return_value.insert.return_value.execute.return_value = mock_response
    
    response = client.post("/api/v1/dcf/save", json=save_payload)
    assert response.status_code == 201

@patch("supabase_client.supabase.table")
def test_delete_wrong_user(mock_table):
    """DELETE /history/{id} wrong user → 403"""
    mock_check = MagicMock()
    mock_check.data = {"user_id": "other-user"}
    mock_table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_check
    
    response = client.delete("/api/v1/dcf/history/123")
    assert response.status_code == 403

@patch("supabase_client.supabase.table")
def test_delete_correct_user(mock_table):
    """DELETE /history/{id} correct user → 200"""
    mock_check = MagicMock()
    mock_check.data = {"user_id": "test-user-uuid"}
    mock_table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_check
    
    mock_delete = MagicMock()
    mock_table.return_value.delete.return_value.eq.return_value.execute.return_value = mock_delete
    
    response = client.delete("/api/v1/dcf/history/123")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
