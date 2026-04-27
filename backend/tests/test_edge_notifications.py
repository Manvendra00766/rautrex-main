import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from services import db_service
from services.alert_service import check_price_alerts
import pandas as pd

@pytest.fixture
def mock_supabase():
    with patch("services.db_service.supabase") as mock_db, \
         patch("services.alert_service.supabase") as mock_alert_db:
        
        # Helper to create a table mock
        def create_table_mock():
            m = MagicMock()
            m.select.return_value = m
            m.eq.return_value = m
            m.order.return_value = m
            m.range.return_value = m
            m.update.return_value = m
            m.insert.return_value = m
            m.execute.return_value = MagicMock(data=[])
            return m
            
        db_table = create_table_mock()
        alert_table = create_table_mock()
        
        mock_db.table.return_value = db_table
        mock_alert_db.table.return_value = alert_table
        
        yield {
            "db": mock_db,
            "alert": mock_alert_db,
            "db_table": db_table,
            "alert_table": alert_table
        }

@pytest.mark.asyncio
async def test_price_alert_same_price(mock_supabase):
    # Alert target = 200, Current price = 200
    alert = {
        "id": "a1", "ticker": "AAPL", "target_price": 200.0, 
        "condition": "above", "user_id": "u1", "is_triggered": False
    }
    
    # 1. Setup checker to find one active alert
    mock_supabase["alert_table"].select().eq().execute.return_value.data = [alert]
    
    # 2. Mock yfinance to return exactly 200.0
    with patch("services.alert_service.yf.download") as mock_yf, \
         patch("services.alert_service.create_notification", new_callable=AsyncMock) as mock_notif:
        
        # Implementation checks if downloaded is empty or 'Close' not in columns
        # Then it does data = downloaded['Close']
        # If len(tickers) == 1, current_prices[tickers[0]] = float(data.iloc[-1])
        
        # Create a DF where 'Close' is a column, and data.iloc[-1] returns the Series of prices
        mock_close = pd.DataFrame({"AAPL": [200.0]}, index=[pd.Timestamp("2023-01-01")])
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.columns = ["Close"]
        mock_df.__getitem__.side_effect = lambda x: mock_close if x == "Close" else MagicMock()
        mock_yf.download.return_value = mock_df
        
        # Run check
        await check_price_alerts()
        
        # Verify it triggered
        assert mock_notif.called
        # Verify it updated is_triggered to True
        mock_supabase["alert_table"].update.assert_called()
        update_args = mock_supabase["alert_table"].update.call_args[0][0]
        assert update_args["is_triggered"] is True

    # 3. Simulate second run where checker doesn't find it anymore (because is_triggered=True)
    # The query in alert_service is .eq("is_triggered", False)
    mock_supabase["alert_table"].select().eq.assert_any_call("is_triggered", False)

@pytest.mark.asyncio
async def test_notification_with_empty_metadata(mock_supabase):
    user_id = "u1"
    # Call with empty metadata
    await db_service.create_notification(user_id, "system", "Title", "Body", metadata={})
    
    # Verify it was passed to insert
    args = mock_supabase["db_table"].insert.call_args[0][0]
    assert args["metadata"] == {}

@pytest.mark.asyncio
async def test_notification_ordering(mock_supabase):
    # This tests the retrieval logic order
    user_id = "u1"
    await db_service.get_notifications(user_id)
    
    # Verify order calls
    # .order("is_read", ascending=True).order("created_at", ascending=False)
    mock_supabase["db_table"].order.assert_any_call("is_read", ascending=True)
    mock_supabase["db_table"].order.assert_any_call("created_at", ascending=False)

@pytest.mark.asyncio
async def test_burst_notifications(mock_supabase):
    user_id = "u1"
    # Create 100 notifications rapidly
    tasks = [
        db_service.create_notification(user_id, "system", f"Title {i}", "Body") 
        for i in range(100)
    ]
    await asyncio.gather(*tasks)
    
    # Verify persist call count
    assert mock_supabase["db_table"].insert.call_count == 100
