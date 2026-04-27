import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from services.signals_service import run_ml_pipeline_stream
from services.notification_service import create_notification
from services.backtester_service import _backtest_sync
from services.db_service import mark_all_read
from services.monte_carlo_service import run_monte_carlo_simulation
from auth import sign_in, refresh_session, User
import json
import pandas as pd
import numpy as np

# --- CONCURRENCY TESTS ---

@pytest.mark.asyncio
async def test_simultaneous_signal_requests():
    # 50 concurrent signal requests for same ticker
    # Requirement: model trained only once
    ticker = "AAPL"
    user_id = "user-1"
    
    # Mock yf and training generators
    with patch("services.signals_service.yf.download") as mock_download:
        
        # Setup mock data with all OHLCV columns to avoid KeyError in technical indicators
        dates = pd.date_range(start="2020-01-01", periods=300)
        df = pd.DataFrame({
            "Open": [100.0]*300, 
            "High": [105.0]*300, 
            "Low": [95.0]*300, 
            "Close": [100.0]*300, 
            "Volume": [1000]*300
        }, index=dates)
        mock_download.return_value = df
        
        # mock_train_lstm is an async generator
        async def mock_gen(*args, **kwargs):
            # Simulate some work to allow concurrent requests to overlap
            await asyncio.sleep(0.1)
            yield {"status": "Training...", "progress": 20}
            yield {"status": "Complete", "progress": 40}
        
        async def run_one():
            res = []
            async for msg in run_ml_pipeline_stream(ticker, user_id):
                res.append(msg)
            return res
            
        # Patching generators in the service module
        with patch("services.signals_service.train_lstm_generator", side_effect=mock_gen) as m_lstm, \
             patch("services.signals_service.train_trend_generator", side_effect=mock_gen), \
             patch("services.signals_service.train_garch_generator", side_effect=mock_gen), \
             patch("services.signals_service.train_anomaly_generator", side_effect=mock_gen), \
             patch("services.signals_service.create_notification", new_callable=AsyncMock):
                 
                 results = await asyncio.gather(*[run_one() for _ in range(50)])
        
        assert len(results) == 50
        # Verification: Only 1 training call because of the Lock in signals_service
        assert m_lstm.call_count == 1 

@pytest.mark.asyncio
async def test_simultaneous_notifications_create():
    # 100 concurrent create_notification calls
    user_id = "user-123"
    
    with patch("services.notification_service.supabase") as mock_sb:
        mock_table = MagicMock()
        mock_sb.table.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[{"id": "n1"}])
        
        tasks = [
            create_notification(user_id, "price_alert", f"Title {i}", "Body")
            for i in range(100)
        ]
        await asyncio.gather(*tasks)
        
        assert mock_table.insert.call_count == 100

@pytest.mark.asyncio
async def test_concurrent_backtest_no_state_bleed():
    # 20 simultaneous backtests for different tickers
    tickers = [f"T{i}" for i in range(20)]
    
    def mock_yf_side_effect(ticker_list, **kwargs):
        # Handle both single ticker and list
        if isinstance(ticker_list, list):
            t = [tk for tk in ticker_list if tk != "^GSPC" and tk != "^NSEI"][0]
        else:
            t = ticker_list
            
        dates = pd.date_range(start="2020-01-01", periods=100)
        tuples = []
        # Expecting MultiIndex (Ticker, Metric)
        # _backtest_sync expects both ticker and benchmark
        bench = "^NSEI" if t.endswith(".NS") else "^GSPC"
        for tk in [t, bench]:
            for c in ["Open", "High", "Low", "Close", "Volume"]:
                tuples.append((tk, c))
        cols = pd.MultiIndex.from_tuples(tuples)
        
        p = 100.0 + int(t[1:])
        data = [[p]*10]*100
        return pd.DataFrame(data, index=dates, columns=cols)

    with patch("services.backtester_service.yf.download", side_effect=mock_yf_side_effect), \
         patch("services.backtester_service.create_notification", new_callable=AsyncMock):
        
        loop = asyncio.get_event_loop()
        tasks = []
        for t in tickers:
            tasks.append(loop.run_in_executor(
                None, _backtest_sync, t, "2020-01-01", "2021-01-01", "momentum", {}, 10000, 0.1, "percent"
            ))
            
        results = await asyncio.gather(*tasks)
        
        for i, res in enumerate(results):
            # If no trades, at least check equity curve length
            assert len(res["chart_data"]) > 0
            # If trades, ensure they are for correct ticker
            if res["trades"]:
                assert all(tr["ticker"] == f"T{i}" for tr in res["trades"])

@pytest.mark.asyncio
async def test_concurrent_mark_all_read_idempotent():
    user_id = "u1"
    with patch("services.db_service.supabase") as mock_sb:
        mock_table = MagicMock()
        mock_sb.table.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.execute.return_value = MagicMock(data=[])
        
        await asyncio.gather(mark_all_read(user_id), mark_all_read(user_id))
        assert mock_table.update.call_count == 2

# --- RECOVERY TESTS ---

@pytest.mark.asyncio
async def test_failed_monte_carlo_no_partial_cache():
    # Monte Carlo fails midway -> check Redis/Cache
    from services.monte_carlo_service import _MC_CACHE
    _MC_CACHE.clear()
    
    tickers = ["FAIL_TICKER"]
    with patch("services.monte_carlo_service.yf.download", side_effect=Exception("Data Fetch Failed")):
        with pytest.raises(ValueError):
            await run_monte_carlo_simulation(tickers, [1.0], 30, 100, 10000)
            
        # Key: Ticker_Horizon_Sims_Capital
        cache_key = "FAIL_TICKER_30_100_10000.0"
        assert cache_key not in _MC_CACHE

@pytest.mark.asyncio
async def test_auth_after_db_restart():
    # Login -> mock DB restart -> use refresh token -> new access token
    email = "test@test.com"
    password = "pass"
    
    with patch("auth.supabase") as mock_sb:
        # 1. Successful Login
        mock_sb.auth.sign_in_with_password.return_value = MagicMock(
            session=MagicMock(access_token="at1", refresh_token="rt1"),
            user=MagicMock(id="u1", email=email),
            error=None
        )
        login_res = await sign_in(email, password)
        assert login_res.session.access_token == "at1"
        
        # 2. Mock DB Restart
        mock_sb.auth.refresh_session.side_effect = [
            MagicMock(session=None, error=MagicMock(message="Service Unavailable", status=503)),
            MagicMock(session=MagicMock(access_token="at2", refresh_token="rt2"), error=None)
        ]
        
        res1 = await refresh_session("rt1")
        assert res1.error.status == 503
        
        res2 = await refresh_session("rt1")
        assert res2.session.access_token == "at2"
