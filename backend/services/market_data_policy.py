import os


LOCAL_ENVIRONMENTS = {"development", "dev", "local", "test", "testing"}
PRODUCTION_ENVIRONMENTS = {"production", "prod", "staging"}


def _env_flag(name: str) -> bool | None:
    raw_value = os.getenv(name)
    if raw_value is None:
        return None
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def is_production_environment() -> bool:
    return os.getenv("ENVIRONMENT", "development").strip().lower() in PRODUCTION_ENVIRONMENTS


def allow_yfinance_fallback() -> bool:
    explicit = _env_flag("ALLOW_YFINANCE_FALLBACK")
    if explicit is not None:
        return explicit
    environment = os.getenv("ENVIRONMENT", "development").strip().lower()
    return environment in LOCAL_ENVIRONMENTS


def is_indian_market_symbol(symbol: str) -> bool:
    normalized = symbol.strip().upper()
    return (
        normalized.endswith(".NS")
        or normalized.endswith(".BO")
        or "GS" in normalized
        or "GB" in normalized
        or normalized.startswith("709GS")
    )
