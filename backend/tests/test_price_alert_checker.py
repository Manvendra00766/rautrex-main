import pytest
import pandas as pd
from unittest.mock import MagicMock, patch, ANY
from services.alert_service import check_price_alerts
from datetime import datetime

@pytest.fixture
def mock_supabase():
    with patch("services.alert_service.supabase") as mock:
        # Setup chained mock for common usage
        mock_table = MagicMock()
        mock.table.return_value = mock_table
        mock_table.select.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        yield mock

@pytest.fixture
def mock_yf():
    with patch("services.alert_service.yf") as mock:
        yield mock

@pytest.fixture
def mock_notification():
    with patch("services.alert_service.create_notification") as mock:
        yield mock

@pytest.mark.asyncio
async def test_scheduler_registered_5min_interval():
    # We need to patch AsyncIOScheduler where it is USED, which is in main.py
    with patch("main.AsyncIOScheduler") as mock_scheduler_class:
        mock_scheduler = mock_scheduler_class.return_value
        from main import lifespan
        from fastapi import FastAPI
        app = FastAPI()
        
        # Trigger lifespan
        async with lifespan(app):
            pass
        
        # Check if add_job was called with 5 minutes
        mock_scheduler.add_job.assert_any_call(
            ANY, # check_price_alerts function
            'interval',
            minutes=5
        )

@pytest.mark.asyncio
async def test_no_active_alerts_skips_early(mock_supabase, mock_yf):
    # Mock no active alerts
    mock_supabase.table().select().eq().execute.return_value.data = []
    
    await check_price_alerts()
    
    mock_yf.download.assert_not_called()

@pytest.mark.asyncio
async def test_unique_tickers_deduped(mock_supabase, mock_yf):
    # 3 AAPL alerts, 2 MSFT alerts
    alerts = [
        {"ticker": "AAPL", "id": 1, "condition": "above", "target_price": 200, "user_id": "u1"},
        {"ticker": "AAPL", "id": 2, "condition": "above", "target_price": 210, "user_id": "u1"},
        {"ticker": "AAPL", "id": 3, "condition": "below", "target_price": 190, "user_id": "u2"},
        {"ticker": "MSFT", "id": 4, "condition": "above", "target_price": 400, "user_id": "u3"},
        {"ticker": "MSFT", "id": 5, "condition": "below", "target_price": 380, "user_id": "u1"},
    ]
    mock_supabase.table().select().eq().execute.return_value.data = alerts
    
    # Mock yf.download to return data for both
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.columns = ["Close"]
    mock_close = pd.DataFrame({
        "AAPL": [205.0],
        "MSFT": [410.0]
    })
    mock_df.__getitem__.side_effect = lambda x: mock_close if x == "Close" else MagicMock()
    mock_yf.download.return_value = mock_df
    
    await check_price_alerts()
    
    # Verify download called once with deduped tickers
    args, _ = mock_yf.download.call_args
    requested_tickers = args[0]
    assert set(requested_tickers) == {"AAPL", "MSFT"}
    assert len(requested_tickers) == 2

@pytest.mark.asyncio
async def test_above_condition_triggers_at_exact_price(mock_supabase, mock_yf, mock_notification):
    alert = {"ticker": "AAPL", "id": 1, "condition": "above", "target_price": 200.0, "user_id": "u1"}
    mock_supabase.table().select().eq().execute.return_value.data = [alert]
    
    # Current price is exactly 200.0
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.columns = ["Close"]
    mock_close = pd.Series([200.0], name="Close")
    mock_df.__getitem__.side_effect = lambda x: mock_close if x == "Close" else MagicMock()
    mock_yf.download.return_value = mock_df
    
    await check_price_alerts()
    
    # Should trigger
    mock_notification.assert_called_once()
    assert mock_supabase.table().update.called

@pytest.mark.asyncio
async def test_above_condition_not_triggered_below(mock_supabase, mock_yf, mock_notification):
    alert = {"ticker": "AAPL", "id": 1, "condition": "above", "target_price": 200.0, "user_id": "u1"}
    mock_supabase.table().select().eq().execute.return_value.data = [alert]
    
    # Current price is 199.99
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.columns = ["Close"]
    mock_close = pd.Series([199.99], name="Close")
    mock_df.__getitem__.side_effect = lambda x: mock_close if x == "Close" else MagicMock()
    mock_yf.download.return_value = mock_df
    
    await check_price_alerts()
    
    # Should NOT trigger
    mock_notification.assert_not_called()

@pytest.mark.asyncio
async def test_below_condition_triggers_at_exact_price(mock_supabase, mock_yf, mock_notification):
    alert = {"ticker": "AAPL", "id": 1, "condition": "below", "target_price": 150.0, "user_id": "u1"}
    mock_supabase.table().select().eq().execute.return_value.data = [alert]
    
    # Current price is exactly 150.0
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.columns = ["Close"]
    mock_close = pd.Series([150.0], name="Close")
    mock_df.__getitem__.side_effect = lambda x: mock_close if x == "Close" else MagicMock()
    mock_yf.download.return_value = mock_df
    
    await check_price_alerts()
    
    # Should trigger
    mock_notification.assert_called_once()

@pytest.mark.asyncio
async def test_below_condition_not_triggered_above(mock_supabase, mock_yf, mock_notification):
    alert = {"ticker": "AAPL", "id": 1, "condition": "below", "target_price": 150.0, "user_id": "u1"}
    mock_supabase.table().select().eq().execute.return_value.data = [alert]
    
    # Current price is 150.01
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.columns = ["Close"]
    mock_close = pd.Series([150.01], name="Close")
    mock_df.__getitem__.side_effect = lambda x: mock_close if x == "Close" else MagicMock()
    mock_yf.download.return_value = mock_df
    
    await check_price_alerts()
    
    # Should NOT trigger
    mock_notification.assert_not_called()

@pytest.mark.asyncio
async def test_triggered_alert_skipped(mock_supabase, mock_yf, mock_notification):
    # The checker filters for is_triggered=False in the query
    # We verify the query call includes this filter
    mock_supabase.table().select().eq().execute.return_value.data = []
    
    await check_price_alerts()
    
    # The first .eq() should be for is_triggered=False
    mock_supabase.table().select().eq.assert_any_call("is_triggered", False)

@pytest.mark.asyncio
async def test_alert_marked_triggered_on_fire(mock_supabase, mock_yf, mock_notification):
    alert = {"ticker": "AAPL", "id": "alert123", "condition": "above", "target_price": 200.0, "user_id": "u1"}
    mock_supabase.table().select().eq().execute.return_value.data = [alert]
    
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.columns = ["Close"]
    mock_close = pd.Series([205.0], name="Close")
    mock_df.__getitem__.side_effect = lambda x: mock_close if x == "Close" else MagicMock()
    mock_yf.download.return_value = mock_df
    
    await check_price_alerts()
    
    # Verify update called with is_triggered: True
    mock_supabase.table().update.assert_called()
    update_args = mock_supabase.table().update.call_args[0][0]
    assert update_args["is_triggered"] is True

@pytest.mark.asyncio
async def test_triggered_at_set(mock_supabase, mock_yf, mock_notification):
    alert = {"ticker": "AAPL", "id": "alert123", "condition": "above", "target_price": 200.0, "user_id": "u1"}
    mock_supabase.table().select().eq().execute.return_value.data = [alert]
    
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.columns = ["Close"]
    mock_close = pd.Series([205.0], name="Close")
    mock_df.__getitem__.side_effect = lambda x: mock_close if x == "Close" else MagicMock()
    mock_yf.download.return_value = mock_df
    
    await check_price_alerts()
    
    # Verify update payload has triggered_at
    update_args = mock_supabase.table().update.call_args[0][0]
    assert "triggered_at" in update_args
    # Verify it looks like an ISO format string
    datetime.fromisoformat(update_args["triggered_at"])

@pytest.mark.asyncio
async def test_notification_created_on_trigger(mock_supabase, mock_yf, mock_notification):
    alert = {"ticker": "AAPL", "id": "alert123", "condition": "above", "target_price": 200.0, "user_id": "u1"}
    mock_supabase.table().select().eq().execute.return_value.data = [alert]
    
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.columns = ["Close"]
    mock_close = pd.Series([205.0], name="Close")
    mock_df.__getitem__.side_effect = lambda x: mock_close if x == "Close" else MagicMock()
    mock_yf.download.return_value = mock_df
    
    await check_price_alerts()
    
    # Verify notification created
    mock_notification.assert_called_once()
    kwargs = mock_notification.call_args[1]
    assert kwargs["type"] == "price_alert"
    assert kwargs["user_id"] == "u1"

@pytest.mark.asyncio
async def test_notification_metadata_has_ticker_and_prices(mock_supabase, mock_yf, mock_notification):
    alert = {"ticker": "AAPL", "id": "alert123", "condition": "above", "target_price": 200.0, "user_id": "u1"}
    mock_supabase.table().select().eq().execute.return_value.data = [alert]
    
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.columns = ["Close"]
    mock_close = pd.Series([205.0], name="Close")
    mock_df.__getitem__.side_effect = lambda x: mock_close if x == "Close" else MagicMock()
    mock_yf.download.return_value = mock_df
    
    await check_price_alerts()
    
    # Verify metadata
    kwargs = mock_notification.call_args[1]
    metadata = kwargs["metadata"]
    assert metadata["ticker"] == "AAPL"
    assert metadata["target_price"] == 200.0
    assert metadata["current_price"] == 205.0

@pytest.mark.asyncio
async def test_yfinance_failure_continues_others(mock_supabase, mock_yf, mock_notification):
    # Two alerts, one fails (missing price), one succeeds
    alerts = [
        {"ticker": "AAPL", "id": 1, "condition": "above", "target_price": 200.0, "user_id": "u1"},
        {"ticker": "MSFT", "id": 2, "condition": "above", "target_price": 300.0, "user_id": "u1"},
    ]
    mock_supabase.table().select().eq().execute.return_value.data = alerts
    
    # Mock yfinance return where MSFT is present but AAPL is NOT in columns or has NaN
    mock_df = MagicMock()
    mock_df.empty = False
    mock_df.columns = ["Close"]
    # Only MSFT in data
    mock_close = pd.DataFrame({
        "MSFT": [310.0]
    })
    mock_df.__getitem__.side_effect = lambda x: mock_close if x == "Close" else MagicMock()
    mock_yf.download.return_value = mock_df
    
    await check_price_alerts()
    
    # MSFT should trigger, AAPL should not (because it was skipped due to missing price)
    assert mock_notification.call_count == 1
    kwargs = mock_notification.call_args[1]
    assert kwargs["metadata"]["ticker"] == "MSFT"

@pytest.mark.asyncio
async def test_checker_handles_empty_prices(mock_supabase, mock_yf, mock_notification):
    alerts = [{"ticker": "AAPL", "id": 1, "condition": "above", "target_price": 200.0, "user_id": "u1"}]
    mock_supabase.table().select().eq().execute.return_value.data = alerts
    
    # Mock yfinance returning empty DF
    mock_df = MagicMock()
    mock_df.empty = True
    mock_yf.download.return_value = mock_df
    
    # Should not crash
    await check_price_alerts()
    mock_notification.assert_not_called()
