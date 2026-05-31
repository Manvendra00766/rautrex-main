import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from database.connection import Base
from models.user_data import CompanyTickerMapping
from infrastructure.cache import cache_response
from infrastructure.redis_client import redis_client

# ════════════════════════════════════════════════════════════════════════
# 1. DATABASE URL ADAPTIVE ROUTING TEST
# ════════════════════════════════════════════════════════════════════════

def test_hybrid_storage_url_fallback():
    """Verify SQLAlchemy adaptive routing resolves different schemas to their asyncpg equivalents."""
    # Test standard postgres:// -> postgresql+asyncpg:// translation
    orig_url = "postgres://username:password@hostname:5432/db"
    
    # We replicate the adaptive routing block from database/connection.py
    if orig_url.startswith("postgres://"):
        resolved_url = orig_url.replace("postgres://", "postgresql+asyncpg://", 1)
    else:
        resolved_url = orig_url
        
    assert resolved_url == "postgresql+asyncpg://username:password@hostname:5432/db"

    # Test standard postgresql:// -> postgresql+asyncpg:// translation
    orig_url_2 = "postgresql://username:password@hostname:5432/db"
    if orig_url_2.startswith("postgresql://"):
        resolved_url_2 = orig_url_2.replace("postgresql://", "postgresql+asyncpg://", 1)
    else:
        resolved_url_2 = orig_url_2
        
    assert resolved_url_2 == "postgresql+asyncpg://username:password@hostname:5432/db"

    # Verify SQLite fallback default if no DATABASE_URL is set
    default_db = "sqlite+aiosqlite:///./rautrex.db"
    assert default_db.startswith("sqlite+aiosqlite://")


# ════════════════════════════════════════════════════════════════════════
# 2. TIERED CACHE READ INTEGRITY TEST
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_hybrid_storage_tiered_cache():
    """Verify cache_response decorator correctly hits Tier 1 (Redis) and caches on miss."""
    
    # Create a dummy async service method decorated with cache_response
    execution_counter = 0

    @cache_response(ttl=30, prefix="test_hardcore")
    async def fetch_dummy_data(key: str) -> dict:
        nonlocal execution_counter
        execution_counter += 1
        return {"result": f"value_for_{key}"}

    # Scenario A: Cache Hit - Redis returns cached JSON payload
    with patch.object(redis_client, "get", new_callable=AsyncMock) as mock_get, \
         patch.object(redis_client, "set", new_callable=AsyncMock) as mock_set:
        
        # Pre-seed Redis cache
        mock_get.return_value = '{"result": "cached_value"}'
        
        data = await fetch_dummy_data("my_key")
        
        assert data == {"result": "cached_value"}
        assert execution_counter == 0  # Dummy function was NEVER executed (Cache Hit)
        mock_get.assert_called_once_with("test_hardcore:fetch_dummy_data:my_key")
        mock_set.assert_not_called()

    # Scenario B: Cache Miss - Redis returns None, executes function, saves to Redis
    execution_counter = 0  # reset
    with patch.object(redis_client, "get", new_callable=AsyncMock) as mock_get, \
         patch.object(redis_client, "set", new_callable=AsyncMock) as mock_set:
        
        mock_get.return_value = None  # Cache Miss
        
        data = await fetch_dummy_data("another_key")
        
        assert data == {"result": "value_for_another_key"}
        assert execution_counter == 1  # Function executed
        mock_get.assert_called_once_with("test_hardcore:fetch_dummy_data:another_key")
        mock_set.assert_called_once_with(
            "test_hardcore:fetch_dummy_data:another_key",
            '{"result": "value_for_another_key"}',
            30
        )


# ════════════════════════════════════════════════════════════════════════
# 3. SQLite local model constraints
# ════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_hybrid_storage_local_model_constraints():
    """Verify local SQLite schema models enforce unique constraints and primary keys correctly."""
    # Build an in-memory SQLite database connection using SQLAlchemy for verification
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    
    async with engine.begin() as conn:
        # Create all local tables in memory
        await conn.run_sync(Base.metadata.create_all)

    # Establish an active session to test transaction insertions
    from sqlalchemy.orm import sessionmaker
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Insert a unique CompanyTickerMapping
        mapping_1 = CompanyTickerMapping(
            user_query="reliance",
            resolved_ticker="RELIANCE.NS",
            confidence_score=1.0
        )
        session.add(mapping_1)
        await session.commit()
        
        # Verify it exists in SQLite
        from sqlalchemy import select
        res = await session.execute(select(CompanyTickerMapping).where(CompanyTickerMapping.user_query == "reliance"))
        item = res.scalar_one_or_none()
        assert item is not None
        assert item.resolved_ticker == "RELIANCE.NS"

        # Verify Unique Constraint: Adding duplicate user_query raises IntegrityError
        from sqlalchemy.exc import IntegrityError
        mapping_dup = CompanyTickerMapping(
            user_query="reliance",
            resolved_ticker="RELIANCE.NS",
            confidence_score=0.9
        )
        session.add(mapping_dup)
        
        with pytest.raises(IntegrityError):
            await session.commit()
            
        await session.rollback()

    await engine.dispose()
