import asyncio
import time
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from infrastructure.time_sync import calibrate_time_offset, offset_calibrated_now, offset_calibrated_datetime
from infrastructure.rate_limiter import TokenBucketRateLimiter
from infrastructure.db_maintenance import run_db_vacuum
from infrastructure.resilient_ws import ResilientWebSocketClient

# ════════════════════════════════════════════════════════════════════════
# 1. API RATE LIMITING & RETRY ON 429 TEST
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_token_bucket_rate_limiter_throttling():
    """Verify TokenBucketRateLimiter limits output and refills properly."""
    # 5 tokens capacity, refill rate 10/s
    limiter = TokenBucketRateLimiter(rate=10.0, capacity=5.0)
    
    # We should be able to acquire 5 immediately
    start_time = time.time()
    for _ in range(5):
        await limiter.acquire()
    elapsed = time.time() - start_time
    assert elapsed < 0.1  # Fast burst

    # The 6th should throttle since bucket is empty
    start_time = time.time()
    await limiter.acquire()
    elapsed = time.time() - start_time
    # Refill rate is 10/s, so refilling 1 token takes 0.1s
    assert elapsed >= 0.05

@pytest.mark.asyncio
async def test_rate_limiter_exponential_backoff_429():
    """Verify exponential backoff blocking when HTTP 429 occurs."""
    limiter = TokenBucketRateLimiter(rate=100.0, capacity=10.0)
    
    # Mock function that fails with 429 on first try, then succeeds
    call_count = 0
    async def mock_api_call():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # We return a dummy object with status_code = 429
            mock_resp = MagicMock()
            mock_resp.status_code = 429
            return mock_resp
        return "success"

    # We patch asyncio.sleep inside acquire/block_for to make tests run instantly
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await limiter.execute(mock_api_call, max_retries=3)
        assert result == "success"
        assert call_count == 2
        
        # Verify it slept during retry sequence (the first sleep is the block wait, second is the acquisition refill sleep)
        assert mock_sleep.call_count >= 1
        # The block state auto-resets when the second call successfully acquires the lock
        assert limiter.is_blocked is False

# ════════════════════════════════════════════════════════════════════════
# 2. TIME SYNCHRONIZATION (CLOCK DRIFT) TEST
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_time_sync_offset_calibration():
    """Verify that calibrate_time_offset correctly queries endpoints and computes drift."""
    
    # Mock httpx response from WorldTimeAPI
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    # Let's say network time is exactly 100 seconds ahead of local system time
    future_time = time.time() + 100.0
    mock_resp.json.return_value = {"unixtime": future_time}

    # Patch httpx.AsyncClient to return our mock
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        
        offset = await calibrate_time_offset()
        
        assert offset > 95.0  # Approx +100s offset (taking round trip into account)
        
        # Verify offset-calibrated methods apply the offset
        now_calibrated = offset_calibrated_now()
        assert now_calibrated > time.time() + 95.0
        
        dt_calibrated = offset_calibrated_datetime()
        assert isinstance(dt_calibrated, datetime)
        assert dt_calibrated.tzinfo == timezone.utc

# ════════════════════════════════════════════════════════════════════════
# 3. SQLITE WAL BLOAT MAINTENANCE TEST
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_database_vacuum_maintenance():
    """Verify daily 4:00 AM SQLite WAL checkpoint and VACUUM maintenance executes safely."""
    # We patch engine inside infrastructure.db_maintenance directly so run_db_vacuum uses the mock
    with patch("infrastructure.db_maintenance.engine") as mock_engine:
        mock_engine.dialect.name = "sqlite"
        
        # Mock engine.connect() context manager yielding a mock connection
        mock_conn = AsyncMock()
        mock_conn.execution_options = MagicMock(return_value=mock_conn)
        
        # Custom deterministic async context manager class
        class MockConnectContext:
            async def __aenter__(self):
                return mock_conn
            async def __aexit__(self, exc_type, exc, tb):
                pass
                
        mock_engine.connect.return_value = MockConnectContext()
        
        success = await run_db_vacuum()
        assert success is True
        
        # Check that BOTH WAL checkpoint and VACUUM were called
        calls = [call[0][0].text for call in mock_conn.execute.call_args_list]
        assert "PRAGMA wal_checkpoint(TRUNCATE);" in calls
        assert "VACUUM;" in calls

# ════════════════════════════════════════════════════════════════════════
# 4. ZOMBIE WEBSOCKET HEARTBEAT & RECONNECT TEST
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_resilient_ws_zombie_detection():
    """Verify that ResilientWebSocketClient identifies a zombie connection and triggers reconnect."""
    client = ResilientWebSocketClient(
        url="ws://dummy",
        ping_interval=0.1,  # Fast ping
        pong_timeout=0.05
    )
    
    # Mock standard websocket connection
    mock_ws = AsyncMock()
    
    # Mock websockets.connect
    with patch("websockets.connect", new_callable=AsyncMock) as mock_connect, \
         patch.object(client, "trigger_reconnect", new_callable=AsyncMock) as mock_reconnect:
        
        mock_connect.return_value = mock_ws
        
        # Scenario: ping fails or times out (raises TimeoutError)
        # Mock ws.ping to return a future that never completes
        loop = asyncio.get_running_loop()
        uncompleted_future = loop.create_future()
        mock_ws.ping.return_value = uncompleted_future
        
        # We start the loops
        client.is_running = True
        client.ws = mock_ws
        
        # Run heartbeat loop once
        heartbeat_task = asyncio.create_task(client._heartbeat_loop())
        # Give it a short moment to run and hit the timeout
        await asyncio.sleep(0.2)
        
        # Cancel tasks and clean up
        client.is_running = False
        heartbeat_task.cancel()
        
        # Verify that trigger_reconnect was called due to the timeout!
        mock_reconnect.assert_called()

# ════════════════════════════════════════════════════════════════════════
# 5. MARKET CALENDAR SERVICE TEST
# ════════════════════════════════════════════════════════════════════════

def test_market_calendar_hours_and_holidays():
    """Verify that MarketCalendarService correctly identifies active sessions, weekends, and holidays."""
    from infrastructure.market_calendar import market_calendar
    from zoneinfo import ZoneInfo
    
    # Scenario A: Standard US market open (Wednesday at 10:00 AM EST)
    open_us_dt = datetime(2026, 6, 3, 10, 0, tzinfo=ZoneInfo("America/New_York"))
    assert market_calendar.is_market_open("AAPL", open_us_dt) is True
    
    # Scenario B: Standard US market closed (Wednesday at 9:00 PM EST)
    closed_us_dt = datetime(2026, 6, 3, 21, 0, tzinfo=ZoneInfo("America/New_York"))
    assert market_calendar.is_market_open("AAPL", closed_us_dt) is False
    
    # Scenario C: Weekend US market closed (Sunday at 12:00 PM EST)
    weekend_us_dt = datetime(2026, 6, 7, 12, 0, tzinfo=ZoneInfo("America/New_York"))
    assert market_calendar.is_market_open("AAPL", weekend_us_dt) is False
    
    # Scenario D: Holiday US market closed (Christmas 2026 at 11:00 AM EST)
    holiday_us_dt = datetime(2026, 12, 25, 11, 0, tzinfo=ZoneInfo("America/New_York"))
    assert market_calendar.is_market_open("AAPL", holiday_us_dt) is False
    
    # Scenario E: Indian Market Open (Wednesday at 11:00 AM IST)
    open_in_dt = datetime(2026, 6, 3, 11, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    assert market_calendar.is_market_open("RELIANCE.NS", open_in_dt) is True
    
    # Scenario F: Indian Market Closed (Wednesday at 5:00 PM IST)
    closed_in_dt = datetime(2026, 6, 3, 17, 0, tzinfo=ZoneInfo("Asia/Kolkata"))
    assert market_calendar.is_market_open("RELIANCE.NS", closed_in_dt) is False
