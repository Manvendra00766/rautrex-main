from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any, Dict, List

import pandas as pd
import yfinance as yf

from services.pricing_engine import get_batch_price_snapshots, get_price_snapshot, get_quote_payload, normalize_symbol
from utils import safe_json


LIQUID_UNIVERSE = [
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
    "META",
    "TSLA",
    "AMD",
    "NFLX",
    "SPY",
    "QQQ",
    "BTC-USD",
    "ETH-USD",
]

INDEX_MAP = {
    "S&P 500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOW JONES": "^DJI",
    "FTSE 100": "^FTSE",
    "DAX": "^GDAXI",
    "NIKKEI 225": "^N225",
    "HANG SENG": "^HSI",
    "NIFTY 50": "^NSEI",
}


def _series_to_chart(history: pd.DataFrame) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for index, row in history.iterrows():
        rows.append(
            {
                "time": pd.Timestamp(index).strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]) if "Volume" in row and not pd.isna(row["Volume"]) else 0,
            }
        )
    return rows


def _search_sync(query: str) -> List[Dict[str, Any]]:
    query = query.strip()
    if not query:
        return []

    results: List[Dict[str, Any]] = []
    try:
        if hasattr(yf, "Search"):
            search = yf.Search(query, max_results=8)
            for item in search.quotes:
                symbol = item.get("symbol")
                if not symbol:
                    continue
                results.append(
                    {
                        "ticker": normalize_symbol(symbol),
                        "name": item.get("shortname") or item.get("longname") or symbol,
                        "exchange": item.get("exchange"),
                        "asset_type": item.get("quoteType") or item.get("typeDisp"),
                    }
                )
    except Exception:
        results = []

    if results:
        return results

    symbol = normalize_symbol(query)
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info or {}
        return [
            {
                "ticker": symbol,
                "name": info.get("longName") or info.get("shortName") or symbol,
                "exchange": info.get("exchange"),
                "asset_type": info.get("quoteType"),
            }
        ]
    except Exception:
        return [{"ticker": symbol, "name": symbol}]


async def search_tickers(query: str, exchange: str = "all"):
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, _search_sync, query)
    if exchange == "all":
        return results
    filtered = []
    for row in results:
        row_exchange = (row.get("exchange") or "").lower()
        if exchange.lower() in row_exchange:
            filtered.append(row)
    return filtered


async def get_quote(ticker: str):
    return safe_json(await get_quote_payload(ticker))


async def get_history(ticker: str, period: str):
    loop = asyncio.get_event_loop()

    def _fetch():
        history = yf.Ticker(ticker).history(period=period, auto_adjust=False)
        if history.empty:
            return []
        return _series_to_chart(history)

    return safe_json(await loop.run_in_executor(None, _fetch))


async def get_fundamentals(ticker: str):
    loop = asyncio.get_event_loop()

    def _fetch():
        info = yf.Ticker(ticker).info or {}
        return {
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "eps": info.get("trailingEps"),
            "revenue": info.get("totalRevenue"),
            "debt_to_equity": info.get("debtToEquity"),
            "roe": info.get("returnOnEquity"),
            "dividend_yield": info.get("dividendYield"),
            "52_week_high": info.get("fiftyTwoWeekHigh"),
            "52_week_low": info.get("fiftyTwoWeekLow"),
            "market_cap": info.get("marketCap"),
            "beta": info.get("beta"),
        }

    return safe_json(await loop.run_in_executor(None, _fetch))


async def get_news(ticker: str):
    loop = asyncio.get_event_loop()

    def _fetch():
        try:
            news = yf.Ticker(ticker).news or []
        except Exception:
            news = []
        rows = []
        for item in news[:20]:
            rows.append(
                {
                    "title": item.get("title"),
                    "publisher": item.get("publisher"),
                    "link": item.get("link"),
                    "time": item.get("providerPublishTime"),
                }
            )
        return rows

    return safe_json(await loop.run_in_executor(None, _fetch))


async def get_info(ticker: str):
    quote = await get_price_snapshot(ticker)
    loop = asyncio.get_event_loop()

    def _fetch():
        info = yf.Ticker(ticker).info or {}
        return {
            "name": info.get("longName") or info.get("shortName") or ticker,
            "sector": info.get("sector") or quote.sector,
            "industry": info.get("industry", "N/A"),
            "description": info.get("longBusinessSummary", ""),
            "country": info.get("country") or quote.country or "",
            "website": info.get("website", ""),
            "employees": info.get("fullTimeEmployees", 0),
            "asset_type": quote.asset_type,
            "exchange": quote.exchange,
            "currency": quote.currency,
        }

    return safe_json(await loop.run_in_executor(None, _fetch))


async def get_indices():
    quotes = await get_batch_price_snapshots(INDEX_MAP.values())
    rows = []
    for name, symbol in INDEX_MAP.items():
        snapshot = quotes.get(normalize_symbol(symbol))
        if not snapshot:
            continue
        rows.append(
            {
                "name": name,
                "ticker": symbol,
                "value": snapshot.last_price,
                "change_percent": snapshot.change_percent,
                "market_cap": snapshot.market_cap,
            }
        )
    return safe_json(rows)


async def get_movers():
    snapshots = await get_batch_price_snapshots(LIQUID_UNIVERSE)
    rows = []
    for symbol, snapshot in snapshots.items():
        rows.append(
            {
                "ticker": symbol,
                "name": snapshot.name,
                "price": snapshot.last_price,
                "change_percent": snapshot.change_percent,
                "volume": snapshot.volume,
                "asset_type": snapshot.asset_type,
            }
        )

    sorted_rows = sorted(rows, key=lambda row: row["change_percent"], reverse=True)
    most_active = sorted(rows, key=lambda row: row.get("volume") or 0, reverse=True)
    return safe_json(
        {
            "gainers": sorted_rows[:5],
            "losers": list(reversed(sorted_rows[-5:])),
            "active": most_active[:5],
        }
    )


async def run_screener():
    snapshots = await get_batch_price_snapshots(LIQUID_UNIVERSE)
    rows = []
    for symbol, snapshot in snapshots.items():
        rows.append(
            {
                "ticker": symbol,
                "name": snapshot.name,
                "price": snapshot.last_price,
                "change_percent": snapshot.change_percent,
                "market_cap": snapshot.market_cap,
                "volume": snapshot.volume,
                "sector": snapshot.sector,
                "country": snapshot.country,
                "asset_type": snapshot.asset_type,
            }
        )
    rows.sort(key=lambda row: ((row.get("market_cap") or 0), (row.get("volume") or 0)), reverse=True)
    return safe_json(rows[:10])
