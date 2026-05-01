import pytest
import asyncio
from unittest.mock import patch, MagicMock
from fastapi import HTTPException
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

# --- PROFILES ---

@pytest.mark.asyncio
async def test_get_profile_calls_correct_table(mock_sb):
    user_id = "user-1"
    mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = make_supabase_response({"id": user_id})
    
    await db_service.get_profile(user_id)
    
    mock_sb.table.assert_called_with("profiles")
    mock_sb.table().select.assert_called_with("*")
    mock_sb.table().select().eq.assert_called_with("id", user_id)

@pytest.mark.asyncio
async def test_get_profile_uses_single(mock_sb):
    user_id = "user-1"
    mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = make_supabase_response({"id": user_id})
    
    await db_service.get_profile(user_id)
    
    mock_sb.table().select().eq().single.assert_called_once()

@pytest.mark.asyncio
async def test_update_profile_full_name(mock_sb):
    user_id = "user-1"
    payload = {"full_name": "New Name"}
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = make_supabase_response(payload)
    
    await db_service.update_profile(user_id, payload)
    
    mock_sb.table().update.assert_called_with(payload)
    mock_sb.table().update().eq.assert_called_with("id", user_id)

@pytest.mark.asyncio
async def test_update_profile_preferences(mock_sb):
    user_id = "user-1"
    payload = {"preferences": {"theme": "light"}}
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = make_supabase_response(payload)
    
    await db_service.update_profile(user_id, payload)
    
    mock_sb.table().update.assert_called_with(payload)

@pytest.mark.asyncio
async def test_avatar_url_stored(mock_sb):
    user_id = "user-1"
    payload = {"avatar_url": "https://example.com/a.png"}
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = make_supabase_response(payload)
    
    await db_service.update_profile(user_id, payload)
    
    mock_sb.table().update.assert_called_with(payload)

# --- PORTFOLIOS ---

@pytest.mark.asyncio
async def test_get_portfolios_filters_by_user(mock_sb):
    user_id = "user-123"
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_portfolios(user_id)
    
    mock_sb.table().select().eq.assert_called_with("user_id", user_id)

@pytest.mark.asyncio
async def test_get_portfolios_includes_positions(mock_sb):
    user_id = "user-123"
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_portfolios(user_id)
    
    mock_sb.table().select.assert_called_with("*, portfolio_positions(*)")

@pytest.mark.asyncio
async def test_create_portfolio_inserts_correct_fields(mock_sb):
    user_id = "u1"
    name = "Growth"
    desc = "High risk"
    # Mock the check for existing portfolios to return empty (meaning this is the first portfolio)
    mock_sb.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = make_supabase_response([])
    mock_sb.table.return_value.insert.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.create_portfolio(user_id, name, desc)
    
    mock_sb.table().insert.assert_called_with({
        "user_id": user_id,
        "name": name,
        "strategy": desc,
        "cash_balance": 0,
        "description": None,
        "is_default": True
    })

@pytest.mark.asyncio
async def test_delete_portfolio_checks_user(mock_sb):
    pid = "p-1"
    uid = "u-1"
    mock_sb.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.delete_portfolio(pid, uid)
    
    # Chained calls: .eq("id", pid).eq("user_id", uid)
    mock_sb.table().delete().eq.assert_any_call("id", pid)
    mock_sb.table().delete().eq().eq.assert_called_with("user_id", uid)

@pytest.mark.asyncio
async def test_add_position_ticker_uppercased(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.add_position("p1", "aapl", "NASDAQ", 10, 150)
    
    args = mock_sb.table().insert.call_args[0][0]
    assert args["ticker"] == "AAPL"

@pytest.mark.asyncio
async def test_add_position_validates_shares_positive(mock_sb):
    with pytest.raises(ValueError, match="Shares must be positive"):
        await db_service.add_position("p1", "AAPL", "NASDAQ", -5, 150)
    
    mock_sb.table.assert_not_called()

@pytest.mark.asyncio
async def test_add_position_validates_cost_positive(mock_sb):
    with pytest.raises(ValueError, match="Average cost price must be positive"):
        await db_service.add_position("p1", "AAPL", "NASDAQ", 10, 0)
    
    mock_sb.table.assert_not_called()

# --- WATCHLISTS ---

@pytest.mark.asyncio
async def test_add_watchlist_item_unique_constraint(mock_sb):
    # Simulate exception from Supabase
    mock_sb.table.return_value.insert.side_effect = Exception("duplicate key value violates unique constraint")
    
    with pytest.raises(HTTPException) as exc:
        await db_service.add_watchlist_item("w1", "AAPL")
    
    assert exc.value.status_code == 409
    assert "already in watchlist" in exc.value.detail

@pytest.mark.asyncio
async def test_watchlist_items_ordered_by_added_at(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_watchlist_items("w1")
    
    mock_sb.table().select().eq().order.assert_called_with("added_at", ascending=True)

# --- SAVED BACKTESTS ---

@pytest.mark.asyncio
async def test_save_backtest_large_results_json(mock_sb):
    large_results = {"data": list(range(500))}
    mock_sb.table.return_value.insert.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.save_backtest("u1", "Test", "AAPL", "SMA", {}, large_results)
    
    args = mock_sb.table().insert.call_args[0][0]
    assert args["results"] == large_results

@pytest.mark.asyncio
async def test_get_backtests_paginated(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.range.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_backtests("u1", limit=10, offset=20)
    
    mock_sb.table().select().eq().range.assert_called_with(20, 29)

@pytest.mark.asyncio
async def test_toggle_favorite(mock_sb):
    mock_sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.toggle_favorite("b1", "u1", True)
    
    mock_sb.table().update.assert_called_with({"is_favorite": True})
    mock_sb.table().update().eq.assert_any_call("id", "b1")

@pytest.mark.asyncio
async def test_delete_backtest_user_scoped(mock_sb):
    mock_sb.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.delete_backtest("b1", "u1")
    
    mock_sb.table().delete().eq.assert_any_call("id", "b1")
    mock_sb.table().delete().eq().eq.assert_called_with("user_id", "u1")

# --- NOTIFICATIONS ---

@pytest.mark.asyncio
async def test_create_notification_is_read_false(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.create_notification("u1", "signal", "Title", "Body")
    
    args = mock_sb.table().insert.call_args[0][0]
    assert args["is_read"] is False

@pytest.mark.asyncio
async def test_create_notification_all_valid_types(mock_sb):
    valid_types = ["signal", "alert", "portfolio", "system", "risk"]
    mock_sb.table.return_value.insert.return_value.execute.return_value = make_supabase_response({})
    
    for t in valid_types:
        await db_service.create_notification("u1", t, "Title", "Body")
        assert mock_sb.table().insert.called

@pytest.mark.asyncio
async def test_create_notification_invalid_type_rejected(mock_sb):
    with pytest.raises(ValueError, match="Invalid notification type"):
        await db_service.create_notification("u1", "unknown", "Title", "Body")
    
    mock_sb.table.assert_not_called()

@pytest.mark.asyncio
async def test_create_notification_empty_metadata_default(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.create_notification("u1", "signal", "Title", "Body")
    
    args = mock_sb.table().insert.call_args[0][0]
    assert args["metadata"] == {}

@pytest.mark.asyncio
async def test_get_notifications_unread_first(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.range.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_notifications("u1")
    
    # First order call should be is_read
    mock_sb.table().select().eq().order.assert_any_call("is_read", ascending=True)

@pytest.mark.asyncio
async def test_get_notifications_created_desc(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.range.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_notifications("u1")
    
    # Second order call should be created_at descending
    mock_sb.table().select().eq().order().order.assert_called_with("created_at", ascending=False)

@pytest.mark.asyncio
async def test_get_notifications_limit(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.order.return_value.range.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_notifications("u1", limit=10, offset=0)
    
    mock_sb.table().select().eq().order().order().range.assert_called_with(0, 9)

@pytest.mark.asyncio
async def test_get_unread_count_returns_int(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response([], count=7)
    
    count = await db_service.get_unread_count("u1")
    assert count == 7

@pytest.mark.asyncio
async def test_get_unread_count_zero_when_none(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response([], count=None)
    
    count = await db_service.get_unread_count("u1")
    assert count == 0

@pytest.mark.asyncio
async def test_mark_read_scoped_to_user(mock_sb):
    mock_sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.mark_read("n1", "u1")
    
    mock_sb.table().update().eq.assert_any_call("id", "n1")
    mock_sb.table().update().eq().eq.assert_called_with("user_id", "u1")

@pytest.mark.asyncio
async def test_mark_all_read_filters_unread(mock_sb):
    mock_sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.mark_all_read("u1")
    
    mock_sb.table().update().eq.assert_any_call("user_id", "u1")
    mock_sb.table().update().eq().eq.assert_called_with("is_read", False)

# --- PRICE ALERTS ---

@pytest.mark.asyncio
async def test_create_alert_condition_validated(mock_sb):
    with pytest.raises(ValueError, match="Invalid alert condition"):
        await db_service.create_price_alert("u1", "AAPL", 150, "sideways")
    
    mock_sb.table.assert_not_called()

@pytest.mark.asyncio
async def test_get_active_alerts_filters_untriggered(mock_sb):
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_active_alerts()
    
    mock_sb.table().select().eq.assert_called_with("is_triggered", False)

@pytest.mark.asyncio
async def test_trigger_alert_sets_fields(mock_sb):
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.trigger_alert("a1")
    
    args = mock_sb.table().update.call_args[0][0]
    assert args["is_triggered"] is True
    assert "triggered_at" in args
