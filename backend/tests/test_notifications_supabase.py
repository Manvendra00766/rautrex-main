import pytest
from unittest.mock import MagicMock, patch
from services.notification_service import (
    create_notification,
    get_notifications,
    get_unread_count,
    mark_read,
    mark_all_read
)

@pytest.fixture
def mock_sb():
    # Use the mock pattern essentially matching the requested target
    with patch("services.notification_service.supabase") as mock:
        yield mock

@pytest.mark.asyncio
async def test_create_notification_inserts_correct_type(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "1"}])
    await create_notification("user1", "signal", "Title", "Body")
    
    # type="signal" → in insert payload
    insert_payload = mock_sb.table.return_value.insert.call_args[0][0]
    assert insert_payload["type"] == "signal"

@pytest.mark.asyncio
async def test_create_notification_is_read_false(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "1"}])
    await create_notification("user1", "signal", "Title", "Body")
    
    # is_read=False always in payload
    insert_payload = mock_sb.table.return_value.insert.call_args[0][0]
    assert insert_payload["is_read"] is False

@pytest.mark.asyncio
async def test_create_notification_all_valid_types(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "1"}])
    valid_types = ["signal", "price_alert", "backtest_complete", "portfolio", "system"]
    
    # loop all 5 types, each inserts without error
    for t in valid_types:
        await create_notification("user1", t, "Title", "Body")
    
    assert mock_sb.table.return_value.insert.call_count == 5

@pytest.mark.asyncio
async def test_create_notification_invalid_type_rejected(mock_sb):
    # type="unknown" → ValueError before insert
    with pytest.raises(ValueError, match="Invalid notification type"):
        await create_notification("user1", "unknown", "Title", "Body")
    
    assert not mock_sb.table.return_value.insert.called

@pytest.mark.asyncio
async def test_create_notification_empty_metadata_default(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"id": "1"}])
    await create_notification("user1", "signal", "Title", "Body")
    
    # no metadata → metadata={} in payload
    insert_payload = mock_sb.table.return_value.insert.call_args[0][0]
    assert insert_payload["metadata"] == {}

@pytest.mark.asyncio
async def test_create_notification_returns_inserted_row(mock_sb):
    mock_row = {"id": "uuid-123"}
    mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[mock_row])
    
    # mock data=[{id:"uuid"}] → function returns it
    result = await create_notification("user1", "signal", "Title", "Body")
    assert result == mock_row

@pytest.mark.asyncio
async def test_get_notifications_limit_applied(mock_sb):
    # Setup chain: table().select().eq().order().order().range()
    mock_query = mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value
    
    await get_notifications("user1", limit=10, offset=0)
    
    # limit=10, offset=0 → .range(0, 9)
    mock_query.range.assert_called_with(0, 9)

@pytest.mark.asyncio
async def test_get_notifications_offset_applied(mock_sb):
    mock_query = mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value
    
    await get_notifications("user1", limit=10, offset=30)
    
    # limit=10, offset=30 → .range(30, 39)
    mock_query.range.assert_called_with(30, 39)

@pytest.mark.asyncio
async def test_get_unread_count_returns_integer(mock_sb):
    # mock count=7 → returns int 7
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(count=7)
    
    count = await get_unread_count("user1")
    assert count == 7
    assert isinstance(count, int)

@pytest.mark.asyncio
async def test_get_unread_count_zero_when_none(mock_sb):
    # count=None → returns 0
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(count=None)
    
    count = await get_unread_count("user1")
    assert count == 0

@pytest.mark.asyncio
async def test_mark_read_requires_both_filters(mock_sb):
    mock_eq = MagicMock()
    mock_sb.table.return_value.update.return_value.eq.return_value = mock_eq
    mock_eq.eq.return_value = mock_eq
    
    await mark_read("user1", "noti_id")
    
    # both .eq("id") and .eq("user_id") called
    # We collect all calls to .eq in the chain
    all_calls = mock_sb.table.return_value.update.return_value.eq.call_args_list + mock_eq.eq.call_args_list
    call_args = [c.args for c in all_calls]
    assert ("id", "noti_id") in call_args
    assert ("user_id", "user1") in call_args

@pytest.mark.asyncio
async def test_mark_all_read_only_updates_unread(mock_sb):
    mock_eq = MagicMock()
    mock_sb.table.return_value.update.return_value.eq.return_value = mock_eq
    mock_eq.eq.return_value = mock_eq
    
    await mark_all_read("user1")
    
    # .eq("is_read", False) in chain
    all_calls = mock_sb.table.return_value.update.return_value.eq.call_args_list + mock_eq.eq.call_args_list
    call_args = [c.args for c in all_calls]
    assert ("is_read", False) in call_args
    assert ("user_id", "user1") in call_args
