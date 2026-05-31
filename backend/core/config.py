import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "RAUTREX Backend"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Security
    SECRET_KEY: str = os.getenv("SUPABASE_JWT_SECRET", os.getenv("SECRET_KEY", "super-secret-key-change-in-production"))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: list[str] = ["*"]
    
    # Market Data
    MARKET_DATA_PROVIDER_URL: str = os.getenv("MARKET_DATA_PROVIDER_URL", "")
    MARKET_DATA_API_KEY: str = os.getenv("MARKET_DATA_API_KEY", "")
    FALLBACK_MARKET_DATA_URL: str = os.getenv("FALLBACK_MARKET_DATA_URL", "")
    FALLBACK_API_KEY: str = os.getenv("FALLBACK_API_KEY", "")

    # Upstox
    UPSTOX_CLIENT_ID: str = os.getenv("UPSTOX_CLIENT_ID", "")
    UPSTOX_CLIENT_SECRET: str = os.getenv("UPSTOX_CLIENT_SECRET", "")
    UPSTOX_REDIRECT_URI: str = os.getenv("UPSTOX_REDIRECT_URI", "")

    # Alpaca
    ALPACA_API_KEY_ID: str = os.getenv("ALPACA_API_KEY_ID", "")
    ALPACA_SECRET_KEY: str = os.getenv("ALPACA_SECRET_KEY", "")
    ALPACA_BASE_URL: str = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

    # OANDA
    OANDA_API_KEY: str = os.getenv("OANDA_API_KEY", "")
    OANDA_ACCOUNT_ID: str = os.getenv("OANDA_ACCOUNT_ID", "")
    OANDA_BASE_URL: str = os.getenv("OANDA_BASE_URL", "https://api-fxpractice.oanda.com")
    
    # Pydantic V2 configuration layout
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()
