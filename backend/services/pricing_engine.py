from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import yfinance as yf

from supabase_client import supabase


UTC = timezone.utc
DEFAULT_CACHE_TTL_SECONDS = 300


@dataclass
class PriceSnapshot:
    symbol: str
    name: str
    asset_type: str
    currency: str
    exchange: Optional[str]
    sector: Optional[str]
    country: Optional[str]
    market_cap: Optional[float]
    previous_close: Optional[float]
    last_price: float
    change_amount: float
    change_percent: float
    volume: Optional[int]
    source: str
    fetched_at: datetime
    raw: Dict[str, Any]

    @property
    def precision(self) -> int:
        return 6 if self.asset_type == "crypto" else 2

    def to_record(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "name": self.name,
            "asset_type": self.asset_type,
            "currency": self.currency,
            "exchange": self.exchange,
            "sector": self.sector,
            "country": self.country,
            "market_cap": self.market_cap,
            "previous_close": self.previous_close,
            "last_price": self.last_price,
            "change_amount": self.change_amount,
            "change_percent": self.change_percent,
            "volume": self.volume,
            "source": self.source,
            "fetched_at": self.fetched_at.isoformat(),
            "raw": self.raw,
        }


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    try:
        if value is None or pd.isna(value):
            return default
        return int(value)
    except Exception:
        return default


def normalize_symbol(symbol: str) -> str:
    s = symbol.strip().upper()
    # Common crypto symbols that people often enter without -USD
    cryptos = {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "DOT", "MATIC"}
    if s in cryptos:
        return f"{s}-USD"
    return s


def infer_asset_type(symbol: str, info: Optional[Dict[str, Any]] = None) -> str:
    info = info or {}
    quote_type = str(info.get("quoteType") or info.get("quote_type") or "").lower()
    if "crypto" in quote_type or symbol.endswith("-USD"):
        return "crypto"
    if "index" in quote_type or symbol.startswith("^"):
        return "index"
    if "etf" in quote_type:
        return "etf"
    return "equity"


def _parse_cached_snapshot(row: Dict[str, Any]) -> Optional[PriceSnapshot]:
    if not row or row.get("last_price") is None:
        return None
    fetched_at_raw = row.get("fetched_at")
    try:
        fetched_at = datetime.fromisoformat(fetched_at_raw.replace("Z", "+00:00")) if fetched_at_raw else _utcnow()
    except Exception:
        fetched_at = _utcnow()
    return PriceSnapshot(
        symbol=normalize_symbol(row["symbol"]),
        name=row.get("name") or row["symbol"],
        asset_type=row.get("asset_type") or infer_asset_type(row["symbol"]),
        currency=row.get("currency") or "USD",
        exchange=row.get("exchange"),
        sector=row.get("sector"),
        country=row.get("country"),
        market_cap=_safe_float(row.get("market_cap")),
        previous_close=_safe_float(row.get("previous_close")),
        last_price=float(row["last_price"]),
        change_amount=_safe_float(row.get("change_amount"), 0.0) or 0.0,
        change_percent=_safe_float(row.get("change_percent"), 0.0) or 0.0,
        volume=_safe_int(row.get("volume")),
        source=row.get("source") or "cache",
        fetched_at=fetched_at,
        raw=row.get("raw") or {},
    )


async def get_cached_price(symbol: str) -> Optional[PriceSnapshot]:
    symbol = normalize_symbol(symbol)
    try:
        response = supabase.table("market_cache").select("*").eq("symbol", symbol).limit(1).execute()
        rows = response.data or []
        return _parse_cached_snapshot(rows[0]) if rows else None
    except Exception:
        return None


async def upsert_cached_price(snapshot: PriceSnapshot) -> None:
    try:
        supabase.table("market_cache").upsert(snapshot.to_record()).execute()
    except Exception:
        # Cache is an optimization. Do not fail pricing on cache write issues.
        return


def _fetch_quote_sync(symbol: str) -> Optional[PriceSnapshot]:
    ticker = yf.Ticker(symbol)
    try:
        history = ticker.history(period="5d", auto_adjust=False)
        if history.empty:
            print(f"Warning: No market data found for {symbol}")
            return None
    except Exception as e:
        print(f"Error fetching history for {symbol}: {e}")
        return None

    info = {}
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    closes = history["Close"].dropna()
    if closes.empty:
        print(f"Warning: No close data found for {symbol}")
        return None


    last_price = float(closes.iloc[-1])
    previous_close = float(closes.iloc[-2]) if len(closes) > 1 else float(info.get("previousClose") or last_price)
    change_amount = last_price - previous_close
    change_percent = (change_amount / previous_close) * 100 if previous_close else 0.0
    asset_type = infer_asset_type(symbol, info)

    return PriceSnapshot(
        symbol=symbol,
        name=info.get("longName") or info.get("shortName") or symbol,
        asset_type=asset_type,
        currency=info.get("currency") or "USD",
        exchange=info.get("exchange") or info.get("fullExchangeName"),
        sector=info.get("sector"),
        country=info.get("country"),
        market_cap=_safe_float(info.get("marketCap")),
        previous_close=previous_close,
        last_price=last_price,
        change_amount=change_amount,
        change_percent=change_percent,
        volume=_safe_int(history["Volume"].dropna().iloc[-1]) if "Volume" in history else None,
        source="yfinance",
        fetched_at=_utcnow(),
        raw={
            "quoteType": info.get("quoteType"),
            "beta": info.get("beta"),
            "trailingPE": info.get("trailingPE"),
        },
    )


async def get_price_snapshot(symbol: str, max_age_seconds: int = DEFAULT_CACHE_TTL_SECONDS) -> Optional[PriceSnapshot]:
    symbol = normalize_symbol(symbol)
    cached = await get_cached_price(symbol)
    if cached and (_utcnow() - cached.fetched_at).total_seconds() <= max_age_seconds:
        return cached

    loop = asyncio.get_event_loop()
    try:
        fresh = await loop.run_in_executor(None, _fetch_quote_sync, symbol)
        if fresh:
            await upsert_cached_price(fresh)
            return fresh
        return cached
    except Exception:
        return cached


async def get_batch_price_snapshots(symbols: Iterable[str], max_age_seconds: int = DEFAULT_CACHE_TTL_SECONDS) -> Dict[str, PriceSnapshot]:
    normalized = [normalize_symbol(symbol) for symbol in symbols if symbol]
    unique_symbols = list(dict.fromkeys(normalized))
    results = await asyncio.gather(
        *[get_price_snapshot(symbol, max_age_seconds=max_age_seconds) for symbol in unique_symbols],
        return_exceptions=True
    )

    mapping: Dict[str, PriceSnapshot] = {}
    for symbol, res in zip(unique_symbols, results):
        if isinstance(res, PriceSnapshot):
            mapping[symbol] = res

    return mapping



def _download_history_sync(symbols: List[str], start: str, end: str) -> Dict[str, pd.Series]:
    if not symbols:
        return {}

    raw = yf.download(symbols, start=start, end=end, progress=False, auto_adjust=False, group_by="ticker")
    if raw.empty:
        return {}

    histories: Dict[str, pd.Series] = {}

    if len(symbols) == 1:
        close_series = raw["Close"] if "Close" in raw else raw.squeeze()
        histories[symbols[0]] = close_series.dropna()
        return histories

    for symbol in symbols:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                close_series = raw[symbol]["Close"].dropna()
            else:
                close_series = raw["Close"].dropna()
            histories[symbol] = close_series
        except Exception:
            continue
    return histories


async def get_price_history(symbols: Iterable[str], start: date, end: date) -> Dict[str, pd.Series]:
    normalized = [normalize_symbol(symbol) for symbol in symbols if symbol]
    unique_symbols = list(dict.fromkeys(normalized))
    if not unique_symbols:
        return {}

    loop = asyncio.get_event_loop()
    histories = await loop.run_in_executor(
        None,
        _download_history_sync,
        unique_symbols,
        start.isoformat(),
        (end + timedelta(days=1)).isoformat(),
    )
    return histories


async def get_quote_payload(symbol: str) -> Dict[str, Any]:
    snapshot = await get_price_snapshot(symbol)
    return {
        "ticker": snapshot.symbol,
        "name": snapshot.name,
        "price": round(snapshot.last_price, snapshot.precision),
        "previous_close": round(snapshot.previous_close or snapshot.last_price, snapshot.precision),
        "change": round(snapshot.change_amount, snapshot.precision),
        "change_percent": round(snapshot.change_percent, 4),
        "volume": snapshot.volume or 0,
        "market_cap": snapshot.market_cap or 0,
        "currency": snapshot.currency,
        "asset_type": snapshot.asset_type,
        "exchange": snapshot.exchange,
        "sector": snapshot.sector,
        "country": snapshot.country,
        "fetched_at": snapshot.fetched_at.isoformat(),
        "source": snapshot.source,
    }
