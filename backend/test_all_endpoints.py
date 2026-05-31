from fastapi.testclient import TestClient
from main import app
from auth import get_current_user

class MockUser:
    id = "test-user-123"
    email = "test@example.com"
    # Mocking db to avoid attribute errors if current_user.db is accessed
    db = type('MockDB', (), {'table': lambda self, x: type('MockTable', (), {'select': lambda *a,**k: type('MockSelect', (), {'eq': lambda *a,**k: type('MockEq', (), {'single': lambda *a,**k: type('MockSingle', (), {'execute': lambda *a,**k: type('MockResponse', (), {'data': {}})()})()})()})()})()})()

def override_get_current_user():
    return MockUser()

app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

def test_portfolio_optimize():
    res = client.post("/api/v1/portfolio/optimize", json={
        "tickers": ["AAPL", "MSFT"],
        "method": "markowitz",
        "objective": "max_sharpe"
    })
    assert res.status_code == 200
    data = res.json()
    assert "weights" in data or "validation" in data

def test_portfolio_rebalance():
    res = client.post("/api/v1/portfolio/rebalance", json={
        "current_positions": [{"ticker": "AAPL", "shares": 10}, {"ticker": "MSFT", "shares": 5}],
        "target_weights": {"AAPL": 0.6, "MSFT": 0.4},
        "threshold": 0.05
    })
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, dict)

def test_backtest_run():
    res = client.post("/api/v1/backtest/run", json={
        "ticker": "AAPL",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "strategy_type": "sma_crossover",
        "strategy_params": {"fast_period": 10, "slow_period": 50},
        "initial_capital": 10000,
        "commission": 0.1,
        "position_sizing": "percent"
    })
    assert res.status_code == 200

def test_compare_strategies():
    res = client.post("/api/v1/compare/strategies", json={
        "ticker": "AAPL",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "strategies": [
            {"name": "SMA", "type": "sma_crossover", "params": {}},
            {"name": "RSI", "type": "rsi_reversion", "params": {}}
        ],
        "initial_capital": 10000
    })
    assert res.status_code == 200

def test_monte_carlo():
    res = client.post("/api/v1/monte-carlo/run", json={
        "ticker": "AAPL",
        "time_horizon": 30,
        "num_simulations": 100,
        "initial_investment": 10000
    })
    assert res.status_code == 200

def test_risk_portfolio():
    res = client.post("/api/v1/risk/portfolio", json={
        "portfolio": [{"ticker": "AAPL", "weight": 0.5}, {"ticker": "MSFT", "weight": 0.5}],
        "start_date": "2023-01-01",
        "end_date": "2023-12-31"
    })
    assert res.status_code == 200

def test_options_price():
    res = client.post("/api/v1/options/price", json={
        "model": "black_scholes",
        "option_type": "call",
        "S": 150,
        "K": 155,
        "T": 0.5,
        "r": 0.05,
        "sigma": 0.2
    })
    assert res.status_code == 200

def test_options_chain():
    res = client.get("/api/v1/options/chain/AAPL")
    assert res.status_code == 200
