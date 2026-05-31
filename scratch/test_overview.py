import asyncio
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.portfolio_engine import get_portfolio_overview

async def main():
    user_id = "d0dfbeb3-bd63-4d3d-89f0-ff419e07190f"
    portfolio_id = "4d85788c-9016-41fe-aa44-c48b42d5cb98"
    
    print("Fetching portfolio overview...")
    data = await get_portfolio_overview(user_id, portfolio_id)
    
    print("\nPositions returned:")
    for pos in data.get("positions", []):
        print(f"Ticker: {pos.get('ticker')}, Shares: {pos.get('shares')}, Avg Cost: {pos.get('avg_cost_per_share')}, Live Price: {pos.get('live_price')}, Unrealized P&L: {pos.get('unrealized_pnl')}, No Live Price: {pos.get('no_live_price')}")
        
    print("\nSummary:")
    summary = data.get("summary") or {}
    print(f"NAV: {summary.get('nav')}, Daily P&L: {summary.get('daily_pnl')}, Unrealized P&L: {summary.get('unrealized_pnl')}")

if __name__ == "__main__":
    asyncio.run(main())
