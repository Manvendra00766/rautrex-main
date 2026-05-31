import asyncio
import json
import hashlib
import yfinance as yf
from typing import List, Optional, Dict, Any
from infrastructure.redis_client import redis_client
from schemas.screener_schema import ScreenerFilterRequest, ScreenerStockResult
from core.logger import logger
import ta

NIFTY50_TICKERS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "INFY.NS", "ITC.NS", "SBIN.NS", "LICI.NS", "HINDUNILVR.NS",
    "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS", "MARUTI.NS", "SUNPHARMA.NS",
    "ADANIENT.NS", "KOTAKBANK.NS", "TITAN.NS", "ULTRACEMCO.NS", "AXISBANK.NS",
    "NTPC.NS", "ASIANPAINT.NS", "ONGC.NS", "ADANIPORTS.NS", "M&M.NS",
    "JSWSTEEL.NS", "TATASTEEL.NS", "COALINDIA.NS", "POWERGRID.NS", "BAJAJ-AUTO.NS",
    "TATAMOTORS.NS", "SBILIFE.NS", "HDFCLIFE.NS", "GRASIM.NS", "NESTLEIND.NS",
    "BRITANNIA.NS", "HINDALCO.NS", "ADANIPOWER.NS", "CIPLA.NS", "EICHERMOT.NS",
    "TECHM.NS", "WIPRO.NS", "ADANIGREEN.NS", "DIVISLAB.NS", "INDUSINDBK.NS",
    "DRREDDY.NS", "BPCL.NS", "APOLLOHOSP.NS", "BAJAJFINSV.NS", "HEROMOTOCO.NS"
]

class ScreenerService:
    def _fetch_stock_data_sync(self, ticker: str) -> Optional[Dict[str, Any]]:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            hist = stock.history(period="3mo")
            rsi = None
            if not hist.empty and len(hist) > 14:
                rsi_indicator = ta.momentum.RSIIndicator(hist['Close'], window=14)
                rsi = float(rsi_indicator.rsi().iloc[-1])
            
            current_price = info.get('currentPrice')
            pe = info.get('trailingPE')
            roe = info.get('returnOnEquity')
            if roe is not None:
                roe = roe * 100  # Convert to percentage
                
            market_cap = info.get('marketCap')
            if market_cap is not None:
                market_cap = market_cap / 1e7  # Convert to Crores
            
            eps = info.get('trailingEps')
            growth_rate = info.get('earningsGrowth', 0.1)
            
            intrinsic_value = None
            dcf_margin = None
            
            if eps and current_price:
                growth_val = growth_rate * 100 if growth_rate < 1 else growth_rate
                intrinsic_value = eps * (8.5 + 2 * growth_val)
                if intrinsic_value > 0:
                    dcf_margin = ((intrinsic_value - current_price) / current_price) * 100
            
            return {
                "symbol": ticker,
                "company_name": info.get('longName', ticker),
                "current_price": current_price,
                "pe_ratio": pe,
                "roe": roe,
                "rsi": rsi,
                "market_cap": market_cap,
                "dcf_margin_of_safety": dcf_margin,
                "signal": "HOLD" # Initial default
            }
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return None

    async def get_stock_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Fetch stock data and calculate metrics with timeout and cache"""
        cache_key = f"screener:ticker:{ticker}"
        
        # 1. Try Cache
        cached = await redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

        # 2. Fetch with Timeout
        loop = asyncio.get_event_loop()
        try:
            data = await asyncio.wait_for(
                loop.run_in_executor(None, self._fetch_stock_data_sync, ticker),
                timeout=5.0
            )
            
            if data:
                await redis_client.set(cache_key, json.dumps(data), ttl=1800)
            return data
            
        except asyncio.TimeoutError:
            logger.warning(f"[SCREENER] Timeout fetching {ticker}")
            return None
        except Exception as e:
            logger.error(f"[SCREENER] Error fetching {ticker}: {e}")
            return None

    def apply_filters(self, stocks: List[Optional[Dict[str, Any]]], filters: ScreenerFilterRequest) -> List[ScreenerStockResult]:
        results = []
        for stock in stocks:
            if not stock:
                continue
                
            pe = stock.get('pe_ratio')
            roe = stock.get('roe')
            rsi = stock.get('rsi')
            market_cap = stock.get('market_cap')
            dcf_margin = stock.get('dcf_margin_of_safety')

            # MISSING DATA != FAILED FILTER. Skip check if value is None.
            
            # P/E Filter
            if pe is not None:
                if filters.min_pe and pe < filters.min_pe: continue
                if filters.max_pe and pe > filters.max_pe: continue
            
            # ROE Filter
            if roe is not None and filters.min_roe:
                if roe < filters.min_roe: continue
            
            # RSI Filter
            if rsi is not None:
                if filters.min_rsi and rsi < filters.min_rsi: continue
                if filters.max_rsi and rsi > filters.max_rsi: continue
            
            # Market Cap Filter
            if market_cap is not None and filters.min_market_cap:
                if market_cap < filters.min_market_cap: continue
            
            # DCF Margin Filter
            if dcf_margin is not None and filters.min_dcf_margin_of_safety:
                if dcf_margin < filters.min_dcf_margin_of_safety: continue

            # Update Signal Badge Logic based on DCF Margin as requested
            if dcf_margin is not None:
                if dcf_margin > 30: stock['signal'] = "STRONG BUY"
                elif dcf_margin > 10: stock['signal'] = "BUY"
                elif dcf_margin > -10: stock['signal'] = "FAIR"
                else: stock['signal'] = "OVERVALUED"
            else:
                stock['signal'] = "N/A"

            results.append(ScreenerStockResult(**stock))
        return results

    async def run_filter(self, filters: ScreenerFilterRequest) -> Dict[str, Any]:
        """Run the screener with filters and caching"""
        logger.info(f"[SCREENER] Received filter request: {filters}")
        
        filter_dict = filters.model_dump(exclude_none=True)
        filter_hash = hashlib.md5(json.dumps(filter_dict, sort_keys=True).encode()).hexdigest()
        cache_key = f"screener:results:{filter_hash}"
        
        cached_res = await redis_client.get(cache_key)
        if cached_res:
            res_data = json.loads(cached_res)
            return {
                "results": [ScreenerStockResult(**item) for item in res_data],
                "cached_tickers": len(res_data),
                "fresh_tickers": 0,
                "status": "Loaded from cache"
            }

        # Run on full Nifty 50
        tasks = [self.get_stock_data(ticker) for ticker in NIFTY50_TICKERS]
        all_stocks = await asyncio.gather(*tasks)
        
        filtered_results = self.apply_filters(all_stocks, filters)

        # Cache global results for 15 minutes
        await redis_client.set(cache_key, json.dumps([r.model_dump() for r in filtered_results]), ttl=900)
        
        return {
            "results": filtered_results,
            "cached_tickers": len(all_stocks),
            "fresh_tickers": len([s for s in all_stocks if s is not None]),
            "status": "Live data fetched"
        }

screener_service = ScreenerService()
