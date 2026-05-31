import asyncio
import yfinance as yf

async def test_assets():
    assets = {
        "Reliance (India)": "RELIANCE.NS",
        "Gold Futures": "GC=F",
        "WTI Crude Oil": "CL=F",
        "Apple (US)": "AAPL"
    }
    
    print("Fetching asset data via yfinance...")
    for name, ticker in assets.items():
        try:
            print(f"\n--- {name} ({ticker}) ---")
            t = yf.Ticker(ticker)
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, lambda: t.info)
            price = info.get("regularMarketPrice") or info.get("currentPrice")
            currency = info.get("currency", "USD")
            print(f"Price: {price} {currency}")
            print(f"Name: {info.get('longName') or info.get('shortName')}")
        except Exception as e:
            print(f"Error fetching {name}: {e}")

if __name__ == "__main__":
    asyncio.run(test_assets())
