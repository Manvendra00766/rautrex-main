from fastapi.testclient import TestClient
from main import app
from dependencies import get_current_user

class MockUser:
    id = "test-user-123"
    email = "test@example.com"

def override_get_current_user():
    return MockUser()

app.dependency_overrides[get_current_user] = override_get_current_user

client = TestClient(app)

def run_tests():
    print("Testing Portfolio Optimize...")
    res = client.post("/api/v1/portfolio/optimize", json={
        "tickers": ["AAPL", "MSFT"],
        "method": "markowitz",
        "objective": "max_sharpe"
    })
    print("Portfolio Optimize:", res.status_code)
    if res.status_code != 200: print(res.json())

    print("Testing Portfolio Rebalance...")
    res = client.post("/api/v1/portfolio/rebalance", json={
        "current_positions": [{"ticker": "AAPL", "shares": 10}, {"ticker": "MSFT", "shares": 5}],
        "target_weights": {"AAPL": 0.6, "MSFT": 0.4},
        "threshold": 0.05
    })
    print("Portfolio Rebalance:", res.status_code)
    if res.status_code != 200: print(res.json())

    print("Testing Backtest Run...")
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
    print("Backtest Run:", res.status_code)
    if res.status_code != 200: print(res.json())

    print("Testing Compare Strategies...")
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
    print("Compare Strategies:", res.status_code)
    if res.status_code != 200: print(res.json())

    print("Testing Monte Carlo...")
    res = client.post("/api/v1/monte-carlo/run", json={
        "ticker": "AAPL",
        "time_horizon": 30,
        "num_simulations": 100,
        "initial_investment": 10000
    })
    print("Monte Carlo:", res.status_code)
    if res.status_code != 200: print(res.json())

    print("Testing Risk Portfolio...")
    res = client.post("/api/v1/risk/portfolio", json={
        "portfolio": [{"ticker": "AAPL", "weight": 0.5}, {"ticker": "MSFT", "weight": 0.5}],
        "start_date": "2023-01-01",
        "end_date": "2023-12-31"
    })
    print("Risk Portfolio:", res.status_code)
    if res.status_code != 200: print(res.json())

    print("Testing Options Price...")
    res = client.post("/api/v1/options/price", json={
        "model": "black_scholes",
        "option_type": "call",
        "S": 150,
        "K": 155,
        "T": 0.5,
        "r": 0.05,
        "sigma": 0.2
    })
    print("Options Price:", res.status_code)
    if res.status_code != 200: print(res.json())

    print("Testing Options Chain...")
    res = client.get("/api/v1/options/chain/AAPL")
    print("Options Chain:", res.status_code)
    if res.status_code != 200: print(res.json())

if __name__ == "__main__":
    run_tests()
