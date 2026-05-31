import asyncio
import os
import json
from pathlib import Path
import sys

# Setup backend imports
sys.path.insert(0, str(Path('./backend').resolve()))

from services.portfolio_engine import get_portfolio_overview

async def main():
    user_id = "d0dfbeb3-bd63-4d3d-89f0-ff419e07190f"
    portfolio_id = "4d85788c-9016-41fe-aa44-c48b42d5cb98"
    
    print(f"Triggering get_portfolio_overview for user={user_id}, portfolio={portfolio_id}...")
    try:
        res = await get_portfolio_overview(user_id, portfolio_id)
        
        print("\n--- RESULTS ---")
        print(f"Portfolio Name: {res.get('name')}")
        print(f"NAV: {res.get('nav')}")
        print(f"Cash Balance: {res.get('cash_balance')}")
        print(f"Holdings Count: {res.get('holdings_count')}")
        
        print("\n--- POSITIONS ---")
        for pos in res.get("positions", []):
            print(f"  Ticker: {pos['ticker']} | Shares: {pos['shares']} | Avg Cost: {pos['avg_cost_per_share']} | Market Value: {pos['market_value']} | Live Price: {pos['live_price']}")
            
        print("\n--- WARNINGS ---")
        for w in res.get("warnings", []):
            print(f"  - {w}")
            
        print("\n--- ALERTS ---")
        for a in res.get("alerts", []):
            print(f"  ID: {a['id']} | Type: {a['type']} | Severity: {a['severity']} | Message: {a['message']}")
            
    except Exception as e:
        print(f"Error during execution: {e}")

if __name__ == "__main__":
    asyncio.run(main())
