import pytest
from fastapi.testclient import TestClient
from main import app
from dependencies import get_current_user
from schemas.paper_trading_schema import Order, Portfolio, Position

client = TestClient(app)

# Mock user object
class MockUser:
    def __init__(self, id):
        self.id = id

async def mock_get_current_user():
    return MockUser(id="test-user-id")

@pytest.fixture
def auth_mock():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    yield
    app.dependency_overrides = {}

def test_place_order_buy_success(auth_mock, mocker):
    """POST /order valid BUY -> 200, returns Order with status EXECUTED"""
    mock_order = Order(
        id="ord_123", user_id="test-user-id", ticker="AAPL", side="BUY",
        quantity=10, order_type="MARKET", executed_price=150.0, status="EXECUTED",
        created_at="2026-05-08T10:00:00"
    )
    mocker.patch("services.paper_trading_service.paper_trading_service.execute_order", return_value=mock_order)
    
    response = client.post("/api/v1/paper/order", json={"ticker": "AAPL", "side": "BUY", "quantity": 10})
    assert response.status_code == 200
    assert response.json()["status"] == "EXECUTED"

def test_place_order_missing_ticker(auth_mock):
    """POST /order missing ticker -> 422"""
    response = client.post("/api/v1/paper/order", json={"side": "BUY", "quantity": 10})
    assert response.status_code == 422

def test_place_order_quantity_zero(auth_mock):
    """POST /order quantity=0 -> 422"""
    response = client.post("/api/v1/paper/order", json={"ticker": "AAPL", "side": "BUY", "quantity": 0})
    assert response.status_code == 422

def test_place_order_sell_rejected(auth_mock, mocker):
    """POST /order SELL rejected -> 200, status REJECTED (not 4xx)"""
    mock_order = Order(
        id="ord_124", user_id="test-user-id", ticker="AAPL", side="SELL",
        quantity=10, order_type="MARKET", executed_price=None, status="REJECTED",
        created_at="2026-05-08T10:00:00"
    )
    mocker.patch("services.paper_trading_service.paper_trading_service.execute_order", return_value=mock_order)
    
    response = client.post("/api/v1/paper/order", json={"ticker": "AAPL", "side": "SELL", "quantity": 10})
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"

def test_get_portfolio_success(auth_mock, mocker):
    """GET /portfolio -> 200, returns Portfolio with positions list"""
    mock_portfolio = Portfolio(
        cash_balance=900000.0, total_invested=100000.0, total_current_value=105000.0,
        total_pnl=5000.0, total_pnl_pct=5.0,
        positions=[Position(ticker="AAPL", quantity=10, avg_buy_price=150.0, current_price=155.0, pnl=50.0, pnl_pct=3.33, total_value=1550.0)]
    )
    mocker.patch("services.paper_trading_service.paper_trading_service.get_portfolio", return_value=mock_portfolio)
    
    response = client.get("/api/v1/paper/portfolio")
    assert response.status_code == 200
    assert len(response.json()["positions"]) == 1

def test_get_portfolio_empty(auth_mock, mocker):
    """GET /portfolio empty (no positions) -> 200, positions=[]"""
    mock_portfolio = Portfolio(
        cash_balance=1000000.0, total_invested=0.0, total_current_value=0.0,
        total_pnl=0.0, total_pnl_pct=0.0, positions=[]
    )
    mocker.patch("services.paper_trading_service.paper_trading_service.get_portfolio", return_value=mock_portfolio)
    
    response = client.get("/api/v1/paper/portfolio")
    assert response.status_code == 200
    assert response.json()["positions"] == []

def test_get_orders_success(auth_mock, mocker):
    """GET /orders -> 200, returns list"""
    mocker.patch("services.paper_trading_service.paper_trading_service.get_orders", return_value=[])
    
    response = client.get("/api/v1/paper/orders")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_reset_account_success(auth_mock, mocker):
    """POST /reset -> 200, cash=1000000 in response"""
    mocker.patch("services.paper_trading_service.paper_trading_service.reset_account")
    
    response = client.post("/api/v1/paper/reset")
    assert response.status_code == 200
    assert response.json()["cash"] == 1000000.0

def test_routes_unauthorized():
    """All routes without auth token -> 401"""
    # Clear overrides to test default behavior (which requires auth header)
    app.dependency_overrides = {}
    response = client.get("/api/v1/paper/portfolio")
    # dependencies.get_current_user raises 401 if header is missing
    assert response.status_code == 401
