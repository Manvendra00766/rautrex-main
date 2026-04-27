import pytest
from unittest.mock import patch, MagicMock, ANY
from services import db_service

# Mock Helper
def make_supabase_response(data=None, count=None):
    mock = MagicMock()
    mock.data = data or []
    mock.count = count
    return mock

@pytest.fixture
def mock_sb():
    with patch("services.db_service.supabase") as mock:
        yield mock

# --- NOTIFICATIONS ---

@pytest.mark.asyncio
async def test_create_notification_is_read_false(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.create_notification("u1", "signal", "Title", "Body")
    
    # Assert is_read=False is always in the payload
    args = mock_sb.table().insert.call_args[0][0]
    assert args["is_read"] is False

@pytest.mark.asyncio
async def test_create_notification_all_valid_types(mock_sb):
    valid_types = ["signal", "alert", "portfolio", "system", "risk"]
    mock_sb.table.return_value.insert.return_value.execute.return_value = make_supabase_response({})
    
    for t in valid_types:
        await db_service.create_notification("u1", t, "Title", "Body")
        assert mock_sb.table().insert.called
        mock_sb.table().insert.reset_mock()

@pytest.mark.asyncio
async def test_create_notification_invalid_type_rejected(mock_sb):
    with pytest.raises(ValueError, match="Invalid notification type"):
        await db_service.create_notification("u1", "unknown", "Title", "Body")
    
    # Should fail before calling Supabase
    mock_sb.table.assert_not_called()

@pytest.mark.asyncio
async def test_create_notification_empty_metadata_default(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.create_notification("u1", "signal", "Title", "Body")
    
    # No metadata param passed -> should default to {}
    args = mock_sb.table().insert.call_args[0][0]
    assert args["metadata"] == {}

@pytest.mark.asyncio
async def test_get_notifications_unread_first(mock_sb):
    # Setup chain
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.range.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_notifications("u1")
    
    # First .order call should be is_read ascending=True
    mock_sb.table().select().eq().order.assert_any_call("is_read", ascending=True)

@pytest.mark.asyncio
async def test_get_notifications_created_desc(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.range.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_notifications("u1")
    
    # Second .order call should be created_at ascending=False (DESC)
    mock_sb.table().select().eq().order().order.assert_called_with("created_at", ascending=False)

@pytest.mark.asyncio
async def test_get_notifications_limit(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.range.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_notifications("u1", limit=10, offset=0)
    
    # Assert .range(0, 9) called
    mock_sb.table().select().eq().order().order().range.assert_called_with(0, 9)

@pytest.mark.asyncio
async def test_get_unread_count_returns_int(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response([], count=7)
    
    count = await db_service.get_unread_count("u1")
    assert count == 7
    assert isinstance(count, int)

@pytest.mark.asyncio
async def test_get_unread_count_zero_when_none(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response([], count=None)
    
    count = await db_service.get_unread_count("u1")
    assert count == 0

@pytest.mark.asyncio
async def test_mark_read_scoped_to_user(mock_sb):
    mock_sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.mark_read("notif-1", "user-1")
    
    # Assert both .eq("id") and .eq("user_id") called
    mock_sb.table().update().eq.assert_any_call("id", "notif-1")
    mock_sb.table().update().eq().eq.assert_called_with("user_id", "user-1")

@pytest.mark.asyncio
async def test_mark_all_read_filters_unread(mock_sb):
    mock_sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.mark_all_read("user-1")
    
    # Assert .eq("is_read", False) in chain to only update unread ones
    mock_sb.table().update().eq().eq.assert_called_with("is_read", False)

# --- PRICE ALERTS ---

@pytest.mark.asyncio
async def test_create_alert_condition_validated(mock_sb):
    with pytest.raises(ValueError, match="Invalid alert condition"):
        await db_service.create_price_alert("u1", "AAPL", 150.0, "sideways")
    
    # Should fail before Supabase call
    mock_sb.table.assert_not_called()

@pytest.mark.asyncio
async def test_get_active_alerts_filters_untriggered(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_active_alerts()
    
    # Assert .eq("is_triggered", False)
    mock_sb.table().select().eq.assert_called_with("is_triggered", False)

@pytest.mark.asyncio
async def test_trigger_alert_sets_fields(mock_sb):
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.trigger_alert("alert-1")
    
    # Assert update with is_triggered=True and triggered_at
    args = mock_sb.table().update.call_args[0][0]
    assert args["is_triggered"] is True
    assert "triggered_at" in args
