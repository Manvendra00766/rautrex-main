import pytest
from unittest.mock import patch, MagicMock
from services.portfolio_engine import create_transaction

@pytest.mark.asyncio
async def test_create_transaction_rejects_buy_if_margin_disabled_and_insufficient_cash():
    user_id = "user123"
    portfolio_id = "port456"
    
    # Mock get_portfolio_record to return margin_enabled=False
    mock_portfolio = {"id": portfolio_id, "margin_enabled": False}
    
    # Mock load_transactions_for_portfolio to return a deposit of 1000
    mock_txs = [
        {"transaction_type": "DEPOSIT", "gross_amount": 1000, "executed_at": "2026-01-01T00:00:00Z", "created_at": "2026-01-01T00:00:00Z"}
    ]
    
    with patch("services.portfolio_engine.get_portfolio_record", return_value=mock_portfolio), \
         patch("services.portfolio_engine.load_transactions_for_portfolio", return_value=mock_txs), \
         patch("services.portfolio_engine.supabase") as mock_supabase:
        
        # Attempt to BUY 10 shares at 200 (Total 2000). Should fail since cash is 1000.
        with pytest.raises(ValueError, match="Insufficient cash for BUY transaction"):
            await create_transaction(user_id, portfolio_id, "BUY", symbol="AAPL", quantity=10, price=200)
            
        # Ensure insert was NOT called
        mock_supabase.table().insert.assert_not_called()

@pytest.mark.asyncio
async def test_create_transaction_allows_buy_if_margin_enabled():
    user_id = "user123"
    portfolio_id = "port456"
    
    # Mock get_portfolio_record to return margin_enabled=True
    mock_portfolio = {"id": portfolio_id, "margin_enabled": True}
    
    # Mock load_transactions_for_portfolio to return a deposit of 1000
    mock_txs = [
        {"transaction_type": "DEPOSIT", "gross_amount": 1000, "executed_at": "2026-01-01T00:00:00Z", "created_at": "2026-01-01T00:00:00Z"}
    ]
    
    with patch("services.portfolio_engine.get_portfolio_record", return_value=mock_portfolio), \
         patch("services.portfolio_engine.load_transactions_for_portfolio", return_value=mock_txs), \
         patch("services.portfolio_engine.supabase") as mock_supabase:
        
        mock_supabase.table().insert.return_value.execute.return_value = MagicMock(data=[{"id": "tx123"}])
        
        # Attempt to BUY 10 shares at 200 (Total 2000). Should succeed since margin is enabled.
        res = await create_transaction(user_id, portfolio_id, "BUY", symbol="AAPL", quantity=10, price=200)
        
        assert res["id"] == "tx123"
        mock_supabase.table().insert.assert_called_once()
