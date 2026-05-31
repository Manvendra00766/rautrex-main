import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
import numpy as np

# Adjust path to import backend modules correctly
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.portfolio_engine import get_portfolio_overview
from services.pricing_engine import PriceSnapshot

@pytest.mark.asyncio
@patch("services.portfolio_engine.supabase.table")
@patch("services.portfolio_engine.get_batch_price_snapshots")
@patch("services.portfolio_engine.get_price_history")
@patch("services.portfolio_engine.persist_historical_equity")
@patch("services.portfolio_engine.sync_portfolio_positions_snapshot")
@patch("requests.get")
async def test_upstox_portfolio_load_success(
    mock_requests_get,
    mock_sync_positions,
    mock_persist_equity,
    mock_price_history,
    mock_price_snapshots,
    mock_supabase_table
):
    # 1. Setup mock portfolio and profiles in Supabase
    mock_portfolio = {
        "id": "mock-upstox-portfolio-id",
        "name": "Upstox Portfolio",
        "strategy": "Imported",
        "initial_cash": 10000.0,
        "cash_balance": 5000.0,
        "created_at": "2026-05-01T00:00:00Z",
    }
    
    mock_profile = {
        "broker_oauth": {
            "broker": "upstox",
            "access_token": "mock-valid-upstox-token"
        }
    }
    
    # Mock Supabase queries
    mock_query_chain = MagicMock()
    mock_query_chain.select.return_value = mock_query_chain
    mock_query_chain.eq.return_value = mock_query_chain
    mock_query_chain.is_.return_value = mock_query_chain
    
    # Setup execute results based on table
    def mock_table_side_effect(table_name):
        res = MagicMock()
        if table_name == "portfolios":
            res.data = [mock_portfolio]
        elif table_name == "profiles":
            res.data = [mock_profile]
        else:
            res.data = []
        
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.is_.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.execute.return_value = res
        return mock_chain
        
    mock_supabase_table.side_effect = mock_table_side_effect
    
    # 2. Mock Upstox API HTTP Responses
    # Fund margin response
    mock_fund_res = MagicMock()
    mock_fund_res.status_code = 200
    mock_fund_res.json.return_value = {
        "status": "success",
        "data": {
            "equity": {
                "available_margin": 12500.0
            }
        }
    }
    
    # Holdings response
    mock_holdings_res = MagicMock()
    mock_holdings_res.status_code = 200
    mock_holdings_res.json.return_value = {
        "status": "success",
        "data": [
            {
                "tradingsymbol": "RELIANCE",
                "quantity": 10.0,
                "average_price": 2400.0,
                "company_name": "Reliance Industries Ltd",
                "isin": "INE002A01018"
            },
            {
                "tradingsymbol": "TCS",
                "quantity": 5.0,
                "average_price": 3200.0,
                "company_name": "Tata Consultancy Services Ltd",
                "isin": "INE467B01029"
            }
        ]
    }
    
    def requests_get_side_effect(url, headers=None, timeout=None):
        if "get-funds-and-margin" in url or "fund-margin" in url:
            return mock_fund_res
        elif "long-term-holdings" in url:
            return mock_holdings_res
        return MagicMock(status_code=404)
        
    mock_requests_get.side_effect = requests_get_side_effect
    
    # 3. Mock Pricing Engine snapshots
    mock_price_snapshots.return_value = {
        "RELIANCE.NS": PriceSnapshot(
            symbol="RELIANCE.NS", name="Reliance Industries Ltd", asset_type="equity", currency="INR", exchange="NSE",
            sector="Energy", country="IN", market_cap=17000000000000, previous_close=2450.0, last_price=2500.0,
            change_amount=50.0, change_percent=2.04, volume=5000000, source="upstox", fetched_at=datetime.now(tz=timezone.utc), raw={}
        ),
        "TCS.NS": PriceSnapshot(
            symbol="TCS.NS", name="Tata Consultancy Services Ltd", asset_type="equity", currency="INR", exchange="NSE",
            sector="Technology", country="IN", market_cap=12000000000000, previous_close=3250.0, last_price=3300.0,
            change_amount=50.0, change_percent=1.54, volume=2000000, source="upstox", fetched_at=datetime.now(tz=timezone.utc), raw={}
        )
    }
    
    mock_price_history.return_value = {}
    
    # 4. Trigger portfolio load
    overview = await get_portfolio_overview(user_id="test-user-id", portfolio_id="mock-upstox-portfolio-id")
    
    # 5. Assertions for success flow
    assert overview["name"] == "Upstox Portfolio"
    assert overview["cash_balance"] == 12500.0  # Synced from Upstox equity.available_margin
    assert overview["holdings_count"] == 2
    
    # Reliance Position assertions
    rel_pos = next(p for p in overview["positions"] if p["ticker"] == "RELIANCE.NS")
    assert rel_pos["shares"] == 10.0
    assert rel_pos["avg_cost_per_share"] == 2400.0
    assert rel_pos["live_price"] == 2500.0
    assert rel_pos["market_value"] == 25000.0
    assert rel_pos["cost_basis"] == 24000.0
    assert rel_pos["unrealized_pnl"] == 1000.0
    
    # TCS Position assertions
    tcs_pos = next(p for p in overview["positions"] if p["ticker"] == "TCS.NS")
    assert tcs_pos["shares"] == 5.0
    assert tcs_pos["avg_cost_per_share"] == 3200.0
    assert tcs_pos["live_price"] == 3300.0
    assert tcs_pos["market_value"] == 16500.0
    assert tcs_pos["cost_basis"] == 16000.0
    assert tcs_pos["unrealized_pnl"] == 500.0
    
    # NAV assertion: market_value (25000 + 16500 = 41500) + cash (12500) = 54000
    assert overview["nav"] == 54000.0
    assert not any("Broker Token Expired" in w for w in overview["warnings"])


@pytest.mark.asyncio
@patch("services.portfolio_engine.supabase.table")
@patch("services.portfolio_engine.load_transactions_for_portfolio")
@patch("services.portfolio_engine.get_batch_price_snapshots")
@patch("services.portfolio_engine.get_price_history")
@patch("services.portfolio_engine.persist_historical_equity")
@patch("services.portfolio_engine.sync_portfolio_positions_snapshot")
@patch("requests.get")
async def test_upstox_portfolio_load_token_expired(
    mock_requests_get,
    mock_sync_positions,
    mock_persist_equity,
    mock_price_history,
    mock_price_snapshots,
    mock_load_transactions,
    mock_supabase_table
):
    # 1. Setup mock portfolio and profiles in Supabase
    mock_portfolio = {
        "id": "mock-upstox-portfolio-id",
        "name": "Upstox Portfolio",
        "strategy": "Imported",
        "initial_cash": 10000.0,
        "cash_balance": 5000.0,
        "created_at": "2026-05-01T00:00:00Z",
    }
    
    mock_profile = {
        "broker_oauth": {
            "broker": "upstox",
            "access_token": "mock-expired-upstox-token"
        }
    }
    
    # Mock Supabase queries
    def mock_table_side_effect(table_name):
        res = MagicMock()
        if table_name == "portfolios":
            res.data = [mock_portfolio]
        elif table_name == "profiles":
            res.data = [mock_profile]
        else:
            res.data = []
        
        mock_chain = MagicMock()
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.is_.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.execute.return_value = res
        return mock_chain
        
    mock_supabase_table.side_effect = mock_table_side_effect
    
    # 2. Mock Upstox API HTTP Responses to return 401 Unauthorized
    mock_401_res = MagicMock()
    mock_401_res.status_code = 401
    mock_401_res.json.return_value = {
        "status": "error",
        "errors": [{"message": "Invalid token"}]
    }
    mock_requests_get.return_value = mock_401_res
    
    # 3. Setup transaction fallback:
    # 10 shares of RELIANCE bought at 2400.0 via transactions
    mock_load_transactions.return_value = [
        {
            "id": "tx-1",
            "user_id": "test-user-id",
            "portfolio_id": "mock-upstox-portfolio-id",
            "symbol": "RELIANCE.NS",
            "transaction_type": "BUY",
            "quantity": 10.0,
            "price": 2400.0,
            "fees": 0.0,
            "executed_at": datetime(2026, 5, 2, tzinfo=timezone.utc),
            "created_at": datetime(2026, 5, 2, tzinfo=timezone.utc),
            "metadata": {}
        }
    ]
    
    # 4. Mock Pricing Engine snapshots
    mock_price_snapshots.return_value = {
        "RELIANCE.NS": PriceSnapshot(
            symbol="RELIANCE.NS", name="Reliance Industries Ltd", asset_type="equity", currency="INR", exchange="NSE",
            sector="Energy", country="IN", market_cap=17000000000000, previous_close=2450.0, last_price=2500.0,
            change_amount=50.0, change_percent=2.04, volume=5000000, source="upstox", fetched_at=datetime.now(tz=timezone.utc), raw={}
        )
    }
    mock_price_history.return_value = {}
    
    # 5. Trigger portfolio load
    overview = await get_portfolio_overview(user_id="test-user-id", portfolio_id="mock-upstox-portfolio-id")
    
    # 6. Assertions for fallback and authentication warnings/alerts
    assert overview["name"] == "Upstox Portfolio"
    assert any("Broker Token Expired" in w for w in overview["warnings"])
    
    # Ensure the broker_auth_required alert is generated
    broker_alerts = [a for a in overview["alerts"] if a["type"] == "broker_auth_required"]
    assert len(broker_alerts) == 1
    assert "re-authenticate" in broker_alerts[0]["message"]
    
    # Verify fallback position is correctly calculated
    rel_pos = next(p for p in overview["positions"] if p["ticker"] == "RELIANCE.NS")
    assert rel_pos["shares"] == 10.0
    assert rel_pos["avg_cost_per_share"] == 2400.0
    assert rel_pos["live_price"] == 2500.0
