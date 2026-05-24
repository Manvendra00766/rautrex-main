import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock, ANY
from httpx import AsyncClient, ASGITransport
from main import app
from dependencies import get_current_user
import pandas as pd
from datetime import datetime

@pytest.fixture(autouse=True)
def override_auth():
    user = MagicMock()
    user.id = "test-user-uuid"
    app.dependency_overrides[get_current_user] = lambda: user
    yield
    app.dependency_overrides = {}

@pytest.fixture
def mock_supabase():
    with patch("supabase_client.supabase.table") as mock:
        yield mock

@pytest.fixture
def mock_ws_manager():
    with patch("websocket_app.manager.manager.broadcast_to_channel", new_callable=AsyncMock) as mock:
        yield mock

@pytest.mark.asyncio
async def test_create_alert(mock_supabase):
    """Test 1: Create alert successfully"""
    mock_table = MagicMock()
    mock_table.insert.return_value.execute.return_value = MagicMock(data=[{"id": "1", "ticker": "RELIANCE.NS"}])
    mock_supabase.return_value = mock_table

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {"ticker": "RELIANCE.NS", "condition": "above", "target_price": 2500}
        response = await ac.post("/api/v1/alerts/", json=payload)
    
    assert response.status_code == 201
    mock_table.insert.assert_called_once()
    insert_data = mock_table.insert.call_args[0][0]
    assert insert_data["user_id"] == "test-user-uuid"
    assert insert_data["ticker"] == "RELIANCE.NS"
    assert insert_data["is_triggered"] is False

@pytest.mark.asyncio
async def test_create_alert_missing_fields():
    """Test 2: Missing fields return 422"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        payload = {"ticker": "RELIANCE.NS", "condition": "above"}
        response = await ac.post("/api/v1/alerts/", json=payload)
    
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_get_alerts(mock_supabase):
    """Test 3: Returns only user's alerts"""
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(data=[{"id": "1", "user_id": "test-user-uuid"}])
    mock_supabase.return_value = mock_table

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/v1/alerts/")
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    mock_table.select.return_value.eq.assert_called_with("user_id", "test-user-uuid")

@pytest.mark.asyncio
async def test_delete_alert_ownership(mock_supabase):
    """Test 4: 403 on deleting other user's alert"""
    mock_table = MagicMock()
    # Mock single() to return other user's ID
    mock_table.select.return_value.eq.return_value.single.return_value = MagicMock(data={"user_id": "other-user"})
    mock_supabase.return_value = mock_table
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.delete("/api/v1/alerts/other-id")
    
    assert response.status_code == 403

@pytest.mark.asyncio
async def test_alert_monitor_triggers_correctly(mock_supabase, mock_ws_manager):
    """Test 5: Monitor triggers and sends WS message"""
    from services.alert_monitor import check_price_alerts
    
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
        {"id": "1", "user_id": "u1", "ticker": "RELIANCE.NS", "condition": "above", "target_price": 2500}
    ])
    mock_supabase.return_value = mock_table

    with patch("yfinance.download") as mock_yf:
        df = pd.DataFrame({"Close": [2600.0]}, index=[datetime.now()])
        mock_yf.return_value = df
        await check_price_alerts()

    # Verify triggered update
    mock_table.update.assert_called_once_with({
        "is_triggered": True,
        "triggered_at": ANY
    })
    
    # Verify WS send
    mock_ws_manager.assert_called_once()
    payload = mock_ws_manager.call_args[0][1]
    assert payload["type"] == "ALERT_TRIGGERED"
    assert payload["symbol"] == "RELIANCE.NS"

@pytest.mark.asyncio
async def test_alert_monitor_no_double_trigger(mock_supabase):
    """Test 6: Triggered alerts not processed"""
    from services.alert_monitor import check_price_alerts
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    mock_supabase.return_value = mock_table
    await check_price_alerts()
    mock_table.select.return_value.eq.assert_called_with("is_triggered", False)

@pytest.mark.asyncio
async def test_alert_monitor_groups_by_symbol(mock_supabase):
    """Test 7: yfinance called once for multiple alerts of same symbol"""
    from services.alert_monitor import check_price_alerts
    mock_table = MagicMock()
    mock_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[
        {"id": "1", "user_id": "u1", "ticker": "AAPL", "condition": "above", "target_price": 150},
        {"id": "2", "user_id": "u1", "ticker": "AAPL", "condition": "below", "target_price": 140},
    ])
    mock_supabase.return_value = mock_table
    with patch("yfinance.download") as mock_yf:
        mock_yf.return_value = pd.DataFrame()
        await check_price_alerts()
    args = mock_yf.call_args[0][0]
    assert len(args) == 1
    assert args[0] == "AAPL"
