import pytest
from unittest.mock import patch, MagicMock, AsyncMock, call
from services.paper_trading_service import PaperTradingService, STARTING_CASH
from schemas.paper_trading_schema import PlaceOrderRequest
from fastapi import HTTPException

@pytest.fixture
def pt_service():
    return PaperTradingService()

@pytest.fixture
def mock_supabase():
    with patch("services.paper_trading_service.supabase") as mocked:
        yield mocked

def test_fetch_price_success(pt_service):
    """fetch_price: yfinance returns valid price"""
    with patch("services.paper_trading_service.yf.Ticker") as mock_ticker:
        mock_stock = MagicMock()
        # Create a mock that doesn't have a 'get' method to test attribute access
        mock_info = MagicMock(spec=['last_price'])
        mock_info.last_price = 2500.0
        mock_stock.fast_info = mock_info
        mock_ticker.return_value = mock_stock
        
        price = pt_service.fetch_price("RELIANCE.NS")
        assert price == 2500.0

def test_fetch_price_failure(pt_service):
    """fetch_price: yfinance returns None → HTTPException 400"""
    with patch("services.paper_trading_service.yf.Ticker") as mock_ticker:
        mock_stock = MagicMock()
        # Ensure it doesn't have 'get' or 'last_price' that return numbers
        mock_stock.fast_info = MagicMock(spec=[]) 
        mock_stock.history.return_value = MagicMock(empty=True)
        mock_ticker.return_value = mock_stock
        
        with pytest.raises(HTTPException) as exc:
            pt_service.fetch_price("INVALID")
        assert exc.value.status_code == 400

@pytest.mark.asyncio
@pytest.mark.parametrize("side,initial_cash,expected_status", [
    ("BUY", 1000000.0, "EXECUTED"),
    ("BUY", 100.0, "REJECTED"),
])
async def test_execute_order_buy_logic(pt_service, mock_supabase, side, initial_cash, expected_status):
    """execute_order BUY: cash validation logic"""
    user_id = "test-user"
    price = 1000.0
    qty = 10
    
    with patch.object(PaperTradingService, 'fetch_price', return_value=price):
        mock_supabase.table().select().eq().execute.return_value.data = [{"user_id": user_id, "cash_balance": initial_cash}]
        mock_supabase.table().insert().execute.return_value.data = [{
            "id": "1", "user_id": user_id, "ticker": "REL", "side": side, "quantity": qty,
            "order_type": "MARKET", "limit_price": None, "executed_price": price if expected_status == "EXECUTED" else None,
            "status": expected_status, "created_at": "now"
        }]
        mock_supabase.table().select().eq().eq().execute.return_value.data = []

        order_req = PlaceOrderRequest(ticker="REL", side=side, quantity=qty)
        order = await pt_service.execute_order(order_req, user_id)
        
        assert order.status == expected_status
        if expected_status == "EXECUTED":
            # Check if cash update was called at some point
            mock_supabase.table("paper_accounts").update.assert_any_call({"cash_balance": initial_cash - (price * qty)})

@pytest.mark.asyncio
async def test_execute_order_sell_success(pt_service, mock_supabase):
    """execute_order SELL: position exists → status EXECUTED, cash increased"""
    user_id = "test-user"
    price = 1000.0
    qty = 5
    initial_cash = 10000.0
    
    with patch.object(PaperTradingService, 'fetch_price', return_value=price):
        mock_supabase.table("paper_accounts").select().eq().execute.return_value.data = [{"user_id": user_id, "cash_balance": initial_cash}]
        mock_supabase.table("paper_positions").select().eq().eq().execute.return_value.data = [
            {"id": "p1", "user_id": user_id, "ticker": "REL", "quantity": 10, "avg_buy_price": 800.0}
        ]
        mock_supabase.table("paper_orders").insert().execute.return_value.data = [{
            "id": "o1", "user_id": user_id, "ticker": "REL", "side": "SELL", "quantity": qty,
            "order_type": "MARKET", "status": "EXECUTED", "created_at": "now", "executed_price": price
        }]
        
        order_req = PlaceOrderRequest(ticker="REL", side="SELL", quantity=qty)
        order = await pt_service.execute_order(order_req, user_id)
        
        assert order.status == "EXECUTED"
        mock_supabase.table("paper_positions").update.assert_any_call({"quantity": 5})
        mock_supabase.table("paper_accounts").update.assert_any_call({"cash_balance": initial_cash + (price * qty)})

@pytest.mark.asyncio
async def test_execute_order_sell_full_delete(pt_service, mock_supabase):
    """execute_order SELL full: position row deleted"""
    user_id = "test-user"
    price = 1000.0
    qty = 10
    
    with patch.object(PaperTradingService, 'fetch_price', return_value=price):
        mock_supabase.table("paper_accounts").select().eq().execute.return_value.data = [{"user_id": user_id, "cash_balance": 10000.0}]
        mock_supabase.table("paper_positions").select().eq().eq().execute.return_value.data = [
            {"id": "p1", "user_id": user_id, "ticker": "REL", "quantity": 10, "avg_buy_price": 800.0}
        ]
        mock_supabase.table("paper_orders").insert().execute.return_value.data = [{"id": "o1", "status": "EXECUTED", "ticker": "REL", "side": "SELL", "quantity": qty, "user_id": user_id, "order_type": "MARKET", "created_at": "now"}]
        
        order_req = PlaceOrderRequest(ticker="REL", side="SELL", quantity=qty)
        await pt_service.execute_order(order_req, user_id)
        
        mock_supabase.table("paper_positions").delete().eq.assert_called_with("id", "p1")

@pytest.mark.asyncio
async def test_avg_price_calculation(pt_service, mock_supabase):
    """avg_price calculation: buy 10@100 then 10@200 → avg=150"""
    user_id = "test-user"
    price = 200.0
    qty = 10
    
    with patch.object(PaperTradingService, 'fetch_price', return_value=price):
        mock_supabase.table("paper_accounts").select().eq().execute.return_value.data = [{"user_id": user_id, "cash_balance": 1000000.0}]
        mock_supabase.table("paper_positions").select().eq().eq().execute.return_value.data = [
            {"id": "p1", "user_id": user_id, "ticker": "REL", "quantity": 10, "avg_buy_price": 100.0}
        ]
        mock_supabase.table("paper_orders").insert().execute.return_value.data = [{"id": "o1", "status": "EXECUTED", "ticker": "REL", "side": "BUY", "quantity": qty, "user_id": user_id, "order_type": "MARKET", "created_at": "now"}]
        
        order_req = PlaceOrderRequest(ticker="REL", side="BUY", quantity=qty)
        await pt_service.execute_order(order_req, user_id)
        
        # Expected new avg = (10*100 + 10*200) / 20 = 150
        mock_supabase.table("paper_positions").update.assert_any_call({
            "quantity": 20,
            "avg_buy_price": pytest.approx(150.0)
        })

@pytest.mark.asyncio
async def test_get_portfolio_pnl(pt_service, mock_supabase):
    """get_portfolio: 2 positions, prices fetched concurrently → correct pnl calc"""
    user_id = "test-user"
    
    # Use side_effect to return different values for different calls if needed, 
    # but here we just need to ensure the chains return the right data.
    def mock_table(name):
        mock = MagicMock()
        if name == "paper_accounts":
            mock.select().eq().execute.return_value.data = [{"cash_balance": 500000.0}]
        elif name == "paper_positions":
            mock.select().eq().execute.return_value.data = [
                {"ticker": "AAPL", "quantity": 10, "avg_buy_price": 150.0},
                {"ticker": "MSFT", "quantity": 5, "avg_buy_price": 300.0}
            ]
        return mock

    mock_supabase.table.side_effect = mock_table
    
    with patch.object(PaperTradingService, 'fetch_price', side_effect=lambda t: 200.0 if t == "AAPL" else 250.0):
        portfolio = await pt_service.get_portfolio(user_id)
        
        assert portfolio.cash_balance == 500000.0
        assert portfolio.total_pnl == 250.0 # (200-150)*10 + (250-300)*5 = 500 - 250 = 250
        assert len(portfolio.positions) == 2

def test_reset_account(pt_service, mock_supabase):
    """reset_account: verify delete called for positions and orders tables"""
    user_id = "test-user"
    pt_service.reset_account(user_id)
    
    assert mock_supabase.table("paper_positions").delete.called
    assert mock_supabase.table("paper_orders").delete.called
    mock_supabase.table("paper_accounts").update.assert_called_with({"cash_balance": STARTING_CASH})
