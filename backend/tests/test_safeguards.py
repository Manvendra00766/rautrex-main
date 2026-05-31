import pytest
import os
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from services.fx_service import fx_rate_service
from services.analytics_worker import analytics_worker_service
from services.corporate_actions import corporate_actions_service
from services.chatbot_context import chatbot_context_service

from models.user_data import UserPortfolio, PortfolioPosition, PortfolioMetricsCache

# ==============================================================================
# SAFEGUARD 2: MULTI-CURRENCY ENGINE TEST
# ==============================================================================
@pytest.mark.asyncio
async def test_fx_rate_service_singleton_and_polling():
    """Verify that FXRateService is a thread-safe singleton and updates rates dynamically."""
    from services.fx_service import FXRateService
    
    srv1 = FXRateService()
    srv2 = FXRateService()
    assert srv1 is srv2  # Confirm singleton
    
    # Mock HTTP response
    yahoo_fx_payload = {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": 83.75
                    }
                }
            ]
        }
    }
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = yahoo_fx_payload
    
    with patch("httpx.AsyncClient.get", return_value=mock_response) as mock_get:
        await fx_rate_service.fetch_latest_rates()
        
        # Verify request parameters
        mock_get.assert_called_once()
        assert "USDINR=X" in mock_get.call_args[0][0]
        
        # Verify in-memory rate updates
        assert fx_rate_service.rates["USD_INR"] == 83.75
        assert fx_rate_service.rates["INR_USD"] == 1.0 / 83.75

# ==============================================================================
# SAFEGUARD 3: TIME-SERIES MATRIX CALCULATIONS & CACHING TEST
# ==============================================================================
@pytest.mark.asyncio
async def test_analytics_worker_numpy_math_and_cache():
    """Verify offline hourly analytics worker executes Sharpe, VaR, Beta, Drawdown, and caches to SQLite."""
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Seeding mock portfolio and position holdings
    portfolio_id = "port-999"
    portfolio = UserPortfolio(id=portfolio_id, user_id="user-111", name="Growth Portfolio")
    position = PortfolioPosition(id=1, portfolio_id=portfolio_id, ticker="AAPL", shares=10, avg_cost_price=150.0)
    
    # Mock database queries
    mock_result_port = MagicMock()
    mock_result_port.scalar_one_or_none.return_value = portfolio
    
    mock_result_pos = MagicMock()
    mock_result_pos.scalars.return_value.all.return_value = [position]
    
    mock_result_metrics = MagicMock()
    mock_result_metrics.scalar_one_or_none.return_value = None
    
    mock_db.execute.side_effect = [mock_result_port, mock_result_pos, mock_result_metrics]
    
    # Create high-fidelity historical prices DataFrame (90 days)
    np.random.seed(42)
    dates = pd.date_range(end="2026-05-30", periods=90)
    # Generate random daily returns centered around small gain
    returns_aapl = np.random.normal(0.001, 0.015, 90)
    returns_spy = np.random.normal(0.0008, 0.011, 90)
    
    prices_aapl = 150 * (1 + returns_aapl).cumprod()
    prices_spy = 500 * (1 + returns_spy).cumprod()
    
    columns = pd.MultiIndex.from_product([["Close"], ["AAPL", "^GSPC"]])
    df_history = pd.DataFrame(
        np.column_stack([prices_aapl, prices_spy]),
        index=dates,
        columns=columns
    )
    
    # Mock yfinance download call
    with patch("yfinance.download", return_value=df_history):
        # Trigger offline calculation
        metrics_entry = await analytics_worker_service.calculate_and_cache_portfolio(portfolio_id, mock_db)
        
        # Verify calculated values
        assert metrics_entry is not None
        assert metrics_entry.portfolio_id == portfolio_id
        assert isinstance(metrics_entry.sharpe_ratio, float)
        assert isinstance(metrics_entry.value_at_risk, float)
        assert isinstance(metrics_entry.max_drawdown, float)
        assert isinstance(metrics_entry.beta, float)
        
        # Assert database commits cached data
        mock_db.commit.assert_called()

# ==============================================================================
# SAFEGUARD 4: CORPORATE ACTIONS INGESTION TEST
# ==============================================================================
@pytest.mark.asyncio
async def test_corporate_actions_atomic_splits():
    """Verify daily cron corporate action splits modify quantities and cost basis atomically and write logs."""
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Seeding position
    position = PortfolioPosition(id=5, portfolio_id="port-999", ticker="AAPL", shares=100.0, avg_cost_price=160.0)
    
    mock_result_aapl = MagicMock()
    mock_result_aapl.scalars.return_value.all.return_value = [position]
    
    mock_result_empty = MagicMock()
    mock_result_empty.scalars.return_value.all.return_value = []
    
    mock_db.execute.side_effect = [mock_result_aapl, mock_result_empty]
    
    # Clear previous mock actions
    log_file = r"D:\projects\rautrex-main\logs\corporate_actions.log"
    if os.path.exists(log_file):
        try:
            os.remove(log_file)
        except Exception:
            pass
            
    # Trigger splits ingestion (2-for-1 split for AAPL)
    await corporate_actions_service.ingest_splits_and_dividends(mock_db)
    
    # Verify split mathematics (shares double, price halves)
    assert position.shares == 200.0
    assert position.avg_cost_price == 80.0
    
    # Verify database was committed atomically
    mock_db.commit.assert_called_once()
    mock_db.rollback.assert_not_called()
    
    # Verify audit trail logs were written permanently
    assert os.path.exists(log_file)
    with open(log_file, "r") as f:
        log_content = f.read()
        assert "AAPL" in log_content
        assert "Shares: 100.0 -> 200.0" in log_content
        assert "SPLIT APPLIED" in log_content

# ==============================================================================
# SAFEGUARD 5: CHATBOT XML RAG CONTEXT INGESTION TEST
# ==============================================================================
@pytest.mark.asyncio
async def test_chatbot_context_rag_injection():
    """Verify that user holdings and cached metrics compile cleanly into structured, verified XML blocks."""
    mock_db = AsyncMock(spec=AsyncSession)
    
    # Seed mock data
    portfolio = UserPortfolio(id="port-999", name="Tactical Asset allocation")
    position = PortfolioPosition(id=1, ticker="RELIANCE.NS", shares=10, avg_cost_price=2400.0)
    metrics = PortfolioMetricsCache(
        portfolio_id="port-999",
        sharpe_ratio=1.95,
        max_drawdown=7.20,
        value_at_risk=2.85,
        beta=1.12
    )
    
    mock_res_port = MagicMock()
    mock_res_port.scalar_one_or_none.return_value = portfolio
    
    mock_res_pos = MagicMock()
    mock_res_pos.scalars.return_value.all.return_value = [position]
    
    mock_res_metrics = MagicMock()
    mock_res_metrics.scalar_one_or_none.return_value = metrics
    
    mock_db.execute.side_effect = [mock_res_port, mock_res_pos, mock_res_metrics]
    
    # Build RAG block
    xml_block = await chatbot_context_service.build_rag_context("user-123", mock_db)
    
    # Verify structured XML nodes exist to guide chatbot answers
    assert "<portfolio_verification_data>" in xml_block
    assert "<positions>" in xml_block
    assert 'ticker="RELIANCE.NS"' in xml_block
    assert 'shares="10"' in xml_block
    assert "<metrics>" in xml_block
    assert "<sharpe_ratio>1.95</sharpe_ratio>" in xml_block
    assert "<max_drawdown>7.2%</max_drawdown>" in xml_block
    assert "<value_at_risk_95>2.85%</value_at_risk_95>" in xml_block
    assert "<beta>1.12</beta>" in xml_block
