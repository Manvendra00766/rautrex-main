import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from dotenv import load_dotenv
from core.logger import logger

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is MISSING")
    logger.error(f"Available env vars with 'DB' or 'DATABASE': {[k for k in os.environ.keys() if 'DB' in k.upper() or 'DATABASE' in k.upper()]}")
    if os.getenv("ENVIRONMENT") == "production":
        raise RuntimeError(
            "DATABASE_URL environment variable is required in production. "
            "Set it in Hugging Face Space Settings -> Secrets."
        )
    DATABASE_URL = "sqlite+aiosqlite:///./rautrex.db"
    logger.info("Using local SQLite fallback for development")

logger.info(f"Raw DATABASE_URL starts with: {DATABASE_URL[:30]}...")

# ── Block SQLite completely in production ──
if os.getenv("ENVIRONMENT") == "production" and DATABASE_URL.startswith("sqlite"):
    raise RuntimeError(f"SQLite not allowed in production. Got: {DATABASE_URL}")

# ── Normalize to asyncpg ──
_normalized = DATABASE_URL
if _normalized.startswith("postgres://"):
    _normalized = _normalized.replace("postgres://", "postgresql+asyncpg://", 1)
elif _normalized.startswith("postgresql://") and not _normalized.startswith("postgresql+asyncpg://"):
    _normalized = _normalized.replace("postgresql://", "postgresql+asyncpg://", 1)

# Add sslmode for cloud providers
if "sslmode" not in _normalized and any(h in _normalized for h in ["supabase", "neon", "aws", "railway", "render"]):
    sep = "&" if "?" in _normalized else "?"
    _normalized = f"{_normalized}{sep}sslmode=require"
    logger.info("Added sslmode=require for cloud PostgreSQL")

DATABASE_URL = _normalized
logger.info(f"Final driver: {DATABASE_URL.split('://')[0]}")

# ── Engine: NullPool for serverless/HF Spaces ──
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    poolclass=NullPool if os.getenv("ENVIRONMENT") == "production" else None,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Tables initialized")

async def close_db():
    await engine.dispose()
    logger.info("Engine disposed")
