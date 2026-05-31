import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from database.connection import Base
from models.user_data import Instrument
from services.ticker_master import ticker_master_service
from services.market_data_service import market_data_service

# ── SQLite Database Setup Fixture ─────────────────────────────────────
@pytest_asyncio.fixture
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_cls = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_cls() as session:
        yield session

    await engine.dispose()

# ════════════════════════════════════════════════════════════════════════
# HARDCORE TICKER MASTER TESTS
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_ticker_master_lazy_sync_flow(async_db):
    """Verify lazy-sync cache HIT/MISS and database persistence logic."""
    symbol = "MSFT"

    # Define mock snapshot returned by the Gateway router
    mock_snapshot = {
        "ticker": "MSFT",
        "price": 420.0,
        "name": "Microsoft Corporation",
        "exchange": "NASDAQ",
        "currency": "USD",
        "sector": "Technology",
        "asset_type": "equity"
    }

    # Scenario A: Cache Miss - Syncs from remote Gateway and saves in SQLite
    with patch.object(market_data_service, "fetch_price", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_snapshot
        
        inst = await ticker_master_service.lazy_sync_ticker(symbol, async_db)
        
        assert inst is not None
        assert inst.symbol == "MSFT"
        assert inst.name == "Microsoft Corporation"
        assert inst.exchange == "NASDAQ"
        assert inst.is_tracked is True
        mock_fetch.assert_called_once_with("MSFT")

    # Scenario B: Cache Hit - Resolves instantly from local SQLite without calling Gateway
    with patch.object(market_data_service, "fetch_price", new_callable=AsyncMock) as mock_fetch_hit:
        inst_hit = await ticker_master_service.lazy_sync_ticker("msft", async_db)  # lowercase input
        
        assert inst_hit is not None
        assert inst_hit.symbol == "MSFT"
        assert inst_hit.name == "Microsoft Corporation"
        mock_fetch_hit.assert_not_called()  # Direct local SQLite resolution!


@pytest.mark.asyncio
async def test_ticker_master_lazy_sync_failures(async_db):
    """Verify that unresolvable remote tickers are handled gracefully without DB pollution."""
    symbol = "INVALID"

    with patch.object(market_data_service, "fetch_price", new_callable=AsyncMock) as mock_fetch:
        # Mocking an unresolvable ticker or gateway dropout (price 0.0 or None)
        mock_fetch.return_value = {"ticker": "INVALID", "price": 0.0}
        
        inst = await ticker_master_service.lazy_sync_ticker(symbol, async_db)
        
        assert inst is None
        mock_fetch.assert_called_once_with("INVALID")


@pytest.mark.asyncio
async def test_ticker_master_daily_cron_sync(async_db):
    """Verify that the daily 4:00 AM cron correctly refreshes only actively tracked assets."""
    # Pre-seed SQLite with two active tracked instruments
    inst1 = Instrument(
        symbol="AAPL",
        name="Apple Inc. (Old)",
        exchange="NASDAQ",
        currency="USD",
        sector="Technology",
        asset_type="equity",
        is_tracked=True
    )
    inst2 = Instrument(
        symbol="RELIANCE.NS",
        name="Reliance Ltd (Old)",
        exchange="NSE",
        currency="INR",
        sector="Energy",
        asset_type="equity",
        is_tracked=True
    )
    # This asset is not tracked, so daily sync should completely IGNORE it
    inst3 = Instrument(
        symbol="UNTRACKED",
        name="Untracked Corp",
        exchange="NYSE",
        currency="USD",
        sector="Retail",
        asset_type="equity",
        is_tracked=False
    )
    async_db.add_all([inst1, inst2, inst3])
    await async_db.commit()

    # Mock the gateway batch retrieval to return updated metadata
    mock_batch_results = {
        "AAPL": {
            "name": "Apple Inc. (New)",
            "exchange": "NASDAQ",
            "currency": "USD",
            "sector": "Tech Giant",
            "asset_type": "equity",
            "price": 180.0
        },
        "RELIANCE.NS": {
            "name": "Reliance Industries Ltd",
            "exchange": "NSE",
            "currency": "INR",
            "sector": "Oil & Telecom",
            "asset_type": "equity",
            "price": 2500.0
        }
    }

    with patch.object(market_data_service, "fetch_batch", new_callable=AsyncMock) as mock_batch:
        mock_batch.return_value = mock_batch_results
        
        results = await ticker_master_service.sync_active_instruments(async_db)
        
        assert results["synced_count"] == 2
        assert results["failures"] == 0
        mock_batch.assert_called_once_with(["AAPL", "RELIANCE.NS"])

    # Verify updates in SQLite
    from sqlalchemy import select
    res = await async_db.execute(select(Instrument).where(Instrument.symbol == "AAPL"))
    aapl = res.scalar_one()
    assert aapl.name == "Apple Inc. (New)"
    assert aapl.sector == "Tech Giant"
    assert aapl.last_synced_at is not None

    res_un = await async_db.execute(select(Instrument).where(Instrument.symbol == "UNTRACKED"))
    untracked = res_un.scalar_one()
    assert untracked.name == "Untracked Corp"  # Unchanged


@pytest.mark.asyncio
async def test_ticker_master_daily_cron_error_isolation(async_db):
    """Verify that a single failed asset during sync does not crash or contaminate the rest of the batch."""
    # Pre-seed two active tracked instruments
    inst1 = Instrument(symbol="AAPL", name="Apple Inc.", is_tracked=True)
    inst2 = Instrument(symbol="RELIANCE.NS", name="Reliance Ltd", is_tracked=True)
    async_db.add_all([inst1, inst2])
    await async_db.commit()

    # Mock batch to omit RELIANCE.NS (simulating a provider API failure)
    mock_batch_results = {
        "AAPL": {
            "name": "Apple Inc. (New)",
            "price": 180.0
        }
    }

    # Also mock single fetch_price to fail for RELIANCE.NS as fallback check
    with patch.object(market_data_service, "fetch_batch", new_callable=AsyncMock) as mock_batch, \
         patch.object(market_data_service, "fetch_price", new_callable=AsyncMock) as mock_single:
        
        mock_batch.return_value = mock_batch_results
        mock_single.return_value = {"price": 0.0}  # failed single fetch fallback
        
        results = await ticker_master_service.sync_active_instruments(async_db)
        
        assert results["synced_count"] == 1
        assert results["failures"] == 1

    # Verify AAPL was updated successfully
    from sqlalchemy import select
    res_aapl = await async_db.execute(select(Instrument).where(Instrument.symbol == "AAPL"))
    aapl = res_aapl.scalar_one()
    assert aapl.name == "Apple Inc. (New)"

    # Verify RELIANCE.NS is unchanged (retains local offline fallback metadata)
    res_rel = await async_db.execute(select(Instrument).where(Instrument.symbol == "RELIANCE.NS"))
    reliance = res_rel.scalar_one()
    assert reliance.name == "Reliance Ltd"
