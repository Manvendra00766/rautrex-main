import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # No defaults for critical env vars — fail fast
    DATABASE_URL: str
    SUPABASE_URL: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    
    # External APIs
    UPSTOX_API_KEY: str | None = None
    UPSTOX_API_SECRET: str | None = None
    TWELVEDATA_API_KEY: str | None = None
    ALPACA_API_KEY: str | None = None
    ALPACA_SECRET_KEY: str | None = None
    
    # Optional
    REDIS_URL: str | None = None
    SENTRY_DSN: str | None = None
    
    # Constants
    RISK_FREE_RATE: float = 0.05
    TRADING_DAYS: int = 252
    
    class Config:
        env_file = None  # Don't read .env in production
        case_sensitive = False

settings = Settings()
