import asyncio
from services.portfolio_service import optimize_portfolio_logic
import json

async def main():
    tickers = ['709GS2074.NS', 'TMPV.NS', 'HINDCOPPER.NS', 'HDFCSML250.NS', 'MIDCAPETF.NS', 'SUZLON.NS', 'BHARATCOAL.NS']
    print(f"Running optimize logic locally for tickers: {tickers}...")
    try:
        res = await optimize_portfolio_logic(
            tickers, "markowitz", "max_sharpe", None, 0.065
        )
        print("Success! Response:")
        print(json.dumps(json.loads(res), indent=2))
    except Exception as e:
        import traceback
        print("Failed! Exception:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
