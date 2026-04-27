import yfinance as yf
import asyncio
# In production, integrate Redis here
# import redis.asyncio as redis

async def search_tickers(query: str):
    # Simulated universal search
    query = query.upper()
    exchanges = ["", ".NS", ".BO", ".L", ".TO", ".AX", ".SI", ".HK"]
    results = [{"ticker": f"{query}{ex}", "name": f"{query} on {ex if ex else 'US'}"} for ex in exchanges[:4]]
    return results

async def get_stock_data(ticker: str, period: str = "1mo"):
    # Run sync yfinance in a thread pool
    loop = asyncio.get_event_loop()
    
    def fetch():
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)
        if hist.empty:
            raise ValueError(f"No data found for {ticker}")
        
        # Format for lightweight charts
        chart_data = []
        for index, row in hist.iterrows():
            chart_data.append({
                "time": index.strftime('%Y-%m-%d'),
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"],
                "value": row["Close"]
            })
        return chart_data

    return await loop.run_in_executor(None, fetch)