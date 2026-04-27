import pytest
from unittest.mock import patch, MagicMock
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
    user_id = "user-123"
    mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = make_supabase_response({"id": user_id})
    
    await db_service.get_profile(user_id)
    
    mock_sb.table.assert_called_with("profiles")
    mock_sb.table().select.assert_called_with("*")
    mock_sb.table().select().eq.assert_called_with("id", user_id)

@pytest.mark.asyncio
async def test_get_profile_uses_single(mock_sb):
    user_id = "user-123"
    mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = make_supabase_response({"id": user_id})
    
    await db_service.get_profile(user_id)
    
    # Assert .single() was called in the chain
    mock_sb.table().select().eq().single.assert_called_once()

@pytest.mark.asyncio
async def test_update_profile_full_name(mock_sb):
    user_id = "user-123"
    data = {"full_name": "New Name"}
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = make_supabase_response(data)
    
    await db_service.update_profile(user_id, data)
    
    mock_sb.table().update.assert_called_with(data)
    mock_sb.table().update().eq.assert_called_with("id", user_id)

@pytest.mark.asyncio
async def test_update_profile_preferences(mock_sb):
    user_id = "user-123"
    data = {"preferences": {"theme": "dark"}}
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = make_supabase_response(data)
    
    await db_service.update_profile(user_id, data)
    
    # Assert preferences field is in the update payload
    args = mock_sb.table().update.call_args[0][0]
    assert "preferences" in args
    assert args["preferences"]["theme"] == "dark"

@pytest.mark.asyncio
async def test_avatar_url_stored(mock_sb):
    user_id = "user-123"
    data = {"avatar_url": "https://example.com/avatar.png"}
    mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = make_supabase_response(data)
    
    await db_service.update_profile(user_id, data)
    
    # Assert avatar_url is in the update payload
    args = mock_sb.table().update.call_args[0][0]
    assert "avatar_url" in args
    assert args["avatar_url"] == "https://example.com/avatar.png"

# --- PORTFOLIOS ---

@pytest.mark.asyncio
async def test_get_portfolios_filters_by_user(mock_sb):
    user_id = "user-123"
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_portfolios(user_id)
    
    # Assert .eq("user_id", user_id) was called
    mock_sb.table().select().eq.assert_called_with("user_id", user_id)

@pytest.mark.asyncio
async def test_get_portfolios_includes_positions(mock_sb):
    user_id = "user-123"
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value = make_supabase_response([])
    
    await db_service.get_portfolios(user_id)
    
    # Assert select("*, portfolio_positions(*)") was used
    mock_sb.table().select.assert_called_with("*, portfolio_positions(*)")

@pytest.mark.asyncio
async def test_create_portfolio_inserts_correct_fields(mock_sb):
    user_id = "u1"
    name = "Growth Portfolio"
    desc = "High risk strategy"
    mock_sb.table.return_value.insert.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.create_portfolio(user_id, name, desc)
    
    mock_sb.table().insert.assert_called_with({
        "user_id": user_id,
        "name": name,
        "description": desc
    })

@pytest.mark.asyncio
async def test_delete_portfolio_checks_user(mock_sb):
    pid = "port-456"
    uid = "user-123"
    mock_sb.table.return_value.delete.return_value.eq.return_value.eq.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.delete_portfolio(pid, uid)
    
    # Assert both .eq("id", pid) and .eq("user_id", uid) were called in chain
    mock_sb.table().delete().eq.assert_any_call("id", pid)
    mock_sb.table().delete().eq().eq.assert_called_with("user_id", uid)

@pytest.mark.asyncio
async def test_add_position_ticker_uppercased(mock_sb):
    mock_sb.table.return_value.insert.return_value.execute.return_value = make_supabase_response({})
    
    await db_service.add_position("p1", "aapl", "NASDAQ", 10, 150)
    
    # Assert ticker "aapl" was converted to "AAPL" in the payload
    args = mock_sb.table().insert.call_args[0][0]
    assert args["ticker"] == "AAPL"

@pytest.mark.asyncio
async def test_add_position_validates_shares_positive(mock_sb):
    with pytest.raises(ValueError, match="Shares must be positive"):
        await db_service.add_position("p1", "AAPL", "NASDAQ", -5, 150)
    
    # Should raise error before calling Supabase
    mock_sb.table.assert_not_called()

@pytest.mark.asyncio
async def test_add_position_validates_cost_positive(mock_sb):
    with pytest.raises(ValueError, match="Average cost price must be positive"):
        await db_service.add_position("p1", "AAPL", "NASDAQ", 10, 0)
    
    # Should raise error before calling Supabase
    mock_sb.table.assert_not_called()
