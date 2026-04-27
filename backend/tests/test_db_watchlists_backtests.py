import pytest
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
    # Patch the supabase client in the db_service module where it's used
    with patch("services.db_service.supabase") as mock:
        yield mock

# --- WATCHLISTS ---

@pytest.mark.asyncio
async def test_add_watchlist_item_unique_constraint(mock_sb):
    # Mock pattern: Simulate unique violation → HTTPException 409
    mock_sb.table.return_value.insert.side_effect = Exception("duplicate key value violates unique constraint")
    
    with pytest.raises(HTTPException) as exc:
        await db_service.add_watchlist_item("w1", "AAPL")
    
    assert exc.value.status_code == 409
    assert "already in watchlist" in exc.value.detail

@pytest.mark.asyncio
async def test_watchlist_items_ordered_by_added_at(mock_sb):
    # Mock pattern: assert .order("added_at", ascending=True)
    mock_sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_watchlist_items("w1")
    
    mock_sb.table().select().eq().order.assert_called_with("added_at", ascending=True)

# --- BACKTESTS ---

@pytest.mark.asyncio
async def test_save_backtest_large_results_json(mock_sb):
    # Mock pattern: 500 entries → full dict in insert, no truncation
    large_results = {"data": list(range(500))}
    mock_sb.table.return_value.insert.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.save_backtest("u1", "Test Backtest", "AAPL", "SMA_Crossover", {"period": 20}, large_results)
    
    args = mock_sb.table().insert.call_args[0][0]
    assert args["results"] == large_results
    assert len(args["results"]["data"]) == 500

@pytest.mark.asyncio
async def test_get_backtests_paginated(mock_sb):
    # Mock pattern: limit=10, offset=20 → assert .range(20, 29)
    mock_sb.table.return_value.select.return_value.eq.return_value.range.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_backtests("u1", limit=10, offset=20)
    
    mock_sb.table().select().eq().range.assert_called_with(20, 29)

@pytest.mark.asyncio
async def test_toggle_favorite(mock_sb):
    # Mock pattern: update is_favorite=True with user_id filter
    mock_sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.toggle_favorite("b1", "u1", True)
    
    mock_sb.table().update.assert_called_with({"is_favorite": True})
    mock_sb.table().update().eq.assert_any_call("id", "b1")
    mock_sb.table().update().eq().eq.assert_called_with("user_id", "u1")

@pytest.mark.asyncio
async def test_delete_backtest_user_scoped(mock_sb):
    # Mock pattern: both id and user_id filters applied
    mock_sb.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.delete_backtest("b1", "u1")
    
    mock_sb.table().delete().eq.assert_any_call("id", "b1")
    mock_sb.table().delete().eq().eq.assert_called_with("user_id", "u1")
