import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from supabase_client import supabase

async def main():
    print("Fetching profiles...")
    profiles = supabase.table("profiles").select("id, broker_oauth").execute()
    print("Profiles:")
    for p in profiles.data or []:
        print(f"ID: {p['id']}, Broker: {p.get('broker_oauth', {}).get('broker') if p.get('broker_oauth') else 'None'}")
        
    print("\nFetching portfolios...")
    portfolios = supabase.table("portfolios").select("id, name, user_id, cash_balance").execute()
    for port in portfolios.data or []:
        print(f"Portfolio ID: {port['id']}, Name: {port['name']}, User: {port['user_id']}, Cash: {port['cash_balance']}")
        
        txs = supabase.table("transactions").select("*").eq("portfolio_id", port["id"]).execute()
        print(f"  Transactions count: {len(txs.data or [])}")
        for t in txs.data or []:
            print(f"    Tx Symbol: {t.get('symbol')}, Type: {t.get('transaction_type')}, Quantity: {t.get('quantity')}, Price: {t.get('price')}")
            
        print("  Positions:")
        pos = supabase.table("portfolio_positions").select("*").eq("portfolio_id", port["id"]).execute()
        for p in pos.data or []:
            print(f"    Ticker: {p['ticker']}, Shares: {p['shares']}, Avg Cost: {p['avg_cost_price']}, Asset Type: {p['asset_type']}")
            
    print("\nFetching market_cache...")
    tickers = ["TMPV.NS", "HINDCOPPER.NS", "SUZLON.NS", "MIDCAPETF.NS", "BHARATCOAL.NS", "HDFCSML250.NS", "709GS2074.NS"]
    for t in tickers:
        res = supabase.table("market_cache").select("*").eq("symbol", t).execute()
        if res.data:
            row = res.data[0]
            print(f"  Ticker: {t}, Last Price: {row.get('last_price')}, Prev Close: {row.get('previous_close')}, Source: {row.get('source')}, Fetched At: {row.get('fetched_at')}")
        else:
            print(f"  Ticker: {t} NOT FOUND IN market_cache")

if __name__ == "__main__":
    asyncio.run(main())
