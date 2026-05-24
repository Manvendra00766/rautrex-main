from fastapi import APIRouter, HTTPException, Query
import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional
import numpy as np

router = APIRouter()

def _normalize_ticker(ticker: str) -> str:
    symbol = ticker.strip().upper()
    if symbol == "APPL":
        raise HTTPException(
            status_code=404,
            detail="Financial data not found for APPL. Did you mean AAPL?",
        )
    return symbol

@router.get("/{ticker}/quote")
async def get_quote(ticker: str):
    symbol = _normalize_ticker(ticker)
    try:
        stock = yf.Ticker(symbol)
        info = stock.info or {}
        price = info.get("regularMarketPrice") or info.get("currentPrice")
        prev_close = info.get("regularMarketPreviousClose") or info.get("previousClose")
        change = (price - prev_close) if (price is not None and prev_close is not None) else None
        change_pct = ((change / prev_close) * 100) if (change is not None and prev_close not in (None, 0)) else None
        return {
            "ticker": symbol,
            "price": price,
            "change": change,
            "change_percent": change_pct,
            "open": info.get("regularMarketOpen"),
            "high": info.get("regularMarketDayHigh"),
            "low": info.get("regularMarketDayLow"),
            "volume": info.get("regularMarketVolume"),
            "market_cap": info.get("marketCap"),
            "currency": info.get("currency"),
            "exchange": info.get("exchange"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{ticker}/info")
async def get_info(ticker: str):
    symbol = _normalize_ticker(ticker)
    try:
        stock = yf.Ticker(symbol)
        info = stock.info or {}
        if not info:
            raise HTTPException(status_code=404, detail=f"Info not found for {symbol}")
        return {
            "ticker": symbol,
            "name": info.get("longName") or info.get("shortName") or symbol,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "website": info.get("website"),
            "description": info.get("longBusinessSummary"),
            "employees": info.get("fullTimeEmployees"),
            "exchange": info.get("exchange"),
            "currency": info.get("currency"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{ticker}/history")
async def get_history(ticker: str, period: str = Query(default="1mo")):
    symbol = _normalize_ticker(ticker)
    try:
        stock = yf.Ticker(symbol)
        hist = stock.history(period=period, auto_adjust=False)
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"Historical data not found for {symbol}")
        hist = hist.reset_index()
        records = []
        for _, row in hist.iterrows():
            date_val = row["Date"]
            
            # Format time for lightweight-charts: YYYY-MM-DD for daily, epoch timestamp for intraday
            if hasattr(date_val, "timestamp"):
                if hasattr(date_val, "hour") and date_val.hour == 0 and date_val.minute == 0 and date_val.second == 0:
                    time_val = date_val.strftime("%Y-%m-%d")
                else:
                    time_val = int(date_val.timestamp())
            else:
                time_val = str(date_val)
                
            records.append({
                "date": date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val),
                "time": time_val,
                "open": float(row["Open"]) if not pd.isna(row["Open"]) else None,
                "high": float(row["High"]) if not pd.isna(row["High"]) else None,
                "low": float(row["Low"]) if not pd.isna(row["Low"]) else None,
                "close": float(row["Close"]) if not pd.isna(row["Close"]) else None,
                "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else None,
            })
        return {"ticker": symbol, "period": period, "history": records, "data": records}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{ticker}/fundamentals")
async def get_fundamentals(ticker: str):
    symbol = _normalize_ticker(ticker)
    try:
        stock = yf.Ticker(symbol)
        info = stock.info or {}
        return {
            "ticker": symbol,
            "pe_ratio": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "pb_ratio": info.get("priceToBook"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "eps": info.get("trailingEps"),
            "forward_eps": info.get("forwardEps"),
            "dividend_yield": info.get("dividendYield"),
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "debt_to_equity": info.get("debtToEquity"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "gross_margin": info.get("grossMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{ticker}/news")
async def get_news(ticker: str):
    symbol = _normalize_ticker(ticker)
    try:
        stock = yf.Ticker(symbol)
        items = stock.news or []
        normalized = []
        for item in items[:20]:
            content = item.get("content", {})
            normalized.append({
                "title": content.get("title") or item.get("title"),
                "summary": content.get("summary"),
                "url": content.get("canonicalUrl", {}).get("url") or item.get("link"),
                "publisher": content.get("provider", {}).get("displayName") or item.get("publisher"),
                "published_at": content.get("pubDate") or item.get("providerPublishTime"),
            })
        return {"ticker": symbol, "news": normalized}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{ticker}")
async def get_financials(ticker: str):
    """
    Fetch key financials for DCF from Yahoo Finance.
    Implements a 3-layer fallback system and strict currency/unit detection.
    """
    try:
        ticker = _normalize_ticker(ticker)
        print(f"\n[STOCKS] Fetching financials for: {ticker}")

        stock = yf.Ticker(ticker)
        
        # 1. Fetch Annual Data
        income_stmt = stock.financials
        balance_sheet = stock.balance_sheet
        cash_flow = stock.cashflow
        info = stock.info

        if income_stmt.empty or balance_sheet.empty or cash_flow.empty:
            print(f"[ERROR] Missing primary financial statements for {ticker}")
            raise HTTPException(status_code=404, detail=f"Financial data not found for {ticker}. Ensure it is a valid ticker and annual data is available.")

        # --- Currency & Exchange Detection ---
        exchange = info.get('exchange', 'Unknown')
        is_indian = ticker.endswith('.NS') or ticker.endswith('.BO') or exchange in ['NSE', 'BSE']
        
        currency = "INR" if is_indian else "USD"
        unit = "Cr" if is_indian else "Mn"
        unit_label = "₹ Cr" if is_indian else "$ Mn"
        divisor = 10**7 if is_indian else 10**6

        # --- State Tracking ---
        warnings = []
        field_sources = {}
        
        def add_warning(msg):
            if msg not in warnings:
                warnings.append(msg)

        # Helper to safely get value from DF with fallback layers
        def get_stat(df, layer1_label, layer2_label, name, idx=0):
            # Layer 1
            try:
                if layer1_label in df.index:
                    val = df.loc[layer1_label].iloc[idx]
                    if not pd.isna(val):
                        field_sources[name] = f"yfinance:{layer1_label}"
                        return float(val)
            except Exception:
                pass
                
            # Layer 2
            try:
                if layer2_label and layer2_label in df.index:
                    val = df.loc[layer2_label].iloc[idx]
                    if not pd.isna(val):
                        field_sources[name] = f"yfinance:{layer2_label} (Layer 2)"
                        return float(val)
            except Exception:
                pass
                
            return None

        # --- 2. Revenue ---
        rev_val = None
        rev_history_raw = []
        try:
            if 'Total Revenue' in income_stmt.index:
                rev_history_raw = income_stmt.loc['Total Revenue']
                field_sources['revenue'] = "yfinance:Total Revenue"
            elif 'Operating Revenue' in income_stmt.index:
                rev_history_raw = income_stmt.loc['Operating Revenue']
                field_sources['revenue'] = "yfinance:Operating Revenue (Layer 2)"
            
            if len(rev_history_raw) > 0:
                available_years = len(rev_history_raw)
                revenue_history = [float(val) for val in rev_history_raw.iloc[:min(available_years, 4)][::-1]]
                rev_val = revenue_history[-1]
            else:
                raise ValueError("No revenue data")
        except Exception:
            raise HTTPException(status_code=404, detail="Total Revenue not found")

        # --- 3. EBIT ---
        ebit = get_stat(income_stmt, 'EBIT', 'Operating Income', 'EBIT')
        
        # --- 4. Tax Rate ---
        net_income = get_stat(income_stmt, 'Net Income', None, 'Net Income')
        pretax_income = get_stat(income_stmt, 'Pretax Income', None, 'Pretax Income')
        
        tax_rate = None
        if net_income is not None and pretax_income is not None and pretax_income != 0:
            tax_rate = 1 - (net_income / pretax_income)
            field_sources['tax_rate'] = "calculated"
        elif info.get('effectiveTaxRateAnnual'):
            tax_rate = info.get('effectiveTaxRateAnnual')
            field_sources['tax_rate'] = "yfinance:info.effectiveTaxRateAnnual (Layer 2)"

        # --- 5. CapEx ---
        capex = get_stat(cash_flow, 'Capital Expenditure', 'Purchase Of PPE', 'CapEx')
        if capex is not None: capex = abs(capex)

        # --- 6. Depreciation ---
        da = get_stat(cash_flow, 'Depreciation And Amortization', 'Reconciled Depreciation', 'D&A')
        if da is None: da = 0.0

        # --- 7. ΔNWC ---
        def get_nwc(idx):
            ca = get_stat(balance_sheet, 'Total Current Assets', 'Current Assets', 'Current Assets', idx)
            cash = get_stat(balance_sheet, 'Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments', 'Cash', idx)
            cl = get_stat(balance_sheet, 'Total Current Liabilities', 'Current Liabilities', 'Current Liabilities', idx)
            st_debt = get_stat(balance_sheet, 'Current Debt', 'Current Debt And Capital Lease Obligation', 'Short Term Debt', idx)
            
            if None in [ca, cash, cl, st_debt]:
                return None
            return (ca - cash) - (cl - st_debt)

        nwc_curr = get_nwc(0)
        nwc_prev = get_nwc(1)
        delta_nwc = 0.0
        if nwc_curr is not None and nwc_prev is not None:
            delta_nwc = nwc_curr - nwc_prev
            field_sources['nwc_change'] = "calculated from balance sheet"
        else:
            field_sources['nwc_change'] = "assumed 0 (missing data)"

        # --- 8. Shares Outstanding ---
        shares = info.get('sharesOutstanding')
        if shares:
            field_sources['shares_outstanding'] = "yfinance:sharesOutstanding"
        elif info.get('impliedSharesOutstanding'):
            shares = info.get('impliedSharesOutstanding')
            field_sources['shares_outstanding'] = "yfinance:impliedSharesOutstanding (Layer 2)"
        
        # Shares are always in Mn
        shares_mn = (shares / 1e6) if shares else 0

        # --- 9. Net Debt ---
        total_debt = info.get('totalDebt')
        total_cash = info.get('totalCash')
        net_debt = None
        if total_debt is not None and total_cash is not None:
            net_debt = (total_debt - total_cash)
            field_sources['net_debt'] = "yfinance:info"

        # --- 10. Market Price ---
        market_price = info.get('currentPrice') or info.get('regularMarketPrice')

        # --- Layer 3: Industry Fallbacks ---
        sector = info.get('sector', 'Default')
        
        ebit_margin_fallbacks = {"Technology": 0.22, "Automobile": 0.08, "Financial Services": 0.28, "Healthcare": 0.18, "Energy": 0.12, "Default": 0.15}
        capex_pct_fallbacks = {"Technology": 0.05, "Automobile": 0.10, "Default": 0.07}

        ebit_margin = ebit / rev_val if ebit is not None and rev_val != 0 else None
        if ebit_margin is None:
            ebit_margin = ebit_margin_fallbacks.get(sector, ebit_margin_fallbacks["Default"])
            field_sources['ebit_margin'] = f"Industry Average ({sector}) (Layer 3)"
            add_warning("EBIT Margin estimated from industry average — enter actual value for accuracy")

        capex_pct = capex / rev_val if capex is not None and rev_val != 0 else None
        if capex_pct is None:
            capex_pct = capex_pct_fallbacks.get(sector, capex_pct_fallbacks["Default"])
            field_sources['capex_pct'] = f"Industry Average ({sector}) (Layer 3)"
            add_warning("CapEx % Rev estimated from industry average — enter actual value for accuracy")
            
        da_pct = da / rev_val if rev_val != 0 else 0.03
        nwc_change_pct = delta_nwc / rev_val if rev_val != 0 else 0.01

        if tax_rate is None:
            tax_rate = 0.25
            field_sources['tax_rate'] = "Global Average (Layer 3)"
            add_warning("Tax Rate estimated from global average — enter actual value for accuracy")

        # --- Normalize Values to Base Unit ---
        normalized_revenue = [r / divisor for r in revenue_history]
        normalized_net_debt = (net_debt / divisor) if net_debt is not None else 0

        return {
            "ticker": ticker,
            "company_name": info.get('longName', ticker),
            "currency": currency,
            "unit": unit,
            "unit_label": unit_label,
            "exchange": exchange,
            "market_price_native": round(market_price, 2) if market_price else 0,
            "revenue": [round(r, 2) for r in normalized_revenue],
            "ebit_margin": round(ebit_margin, 4),
            "tax_rate": round(max(0, min(tax_rate, 0.5)), 4),
            "capex_pct": round(capex_pct, 4),
            "da_pct": round(da_pct, 4),
            "nwc_change_pct": round(nwc_change_pct, 4),
            "shares_outstanding": round(shares_mn, 2),
            "net_debt": round(normalized_net_debt, 2),
            "current_market_price": round(market_price, 2) if market_price else 0,
            "warnings": warnings,
            "field_sources": field_sources
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))
