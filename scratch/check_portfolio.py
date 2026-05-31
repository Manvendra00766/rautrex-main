import os
import asyncio
import sys

# Add backend directory to sys.path so we can import services
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append("backend")

from dotenv import load_dotenv
load_dotenv("backend/.env")

from supabase_client import supabase
from services.portfolio_engine import get_portfolio_overview

async def main():
    email = "rautelamanvendra07@gmail.com"
    print(f"Finding profile for email: {email}...")
    
    # Get user by email or get any profile
    res = supabase.table("profiles").select("*").execute()
    if not res.data:
        print("No profiles found!")
        return
        
    user = None
    for row in res.data:
        # Check if email is in the row (e.g. metadata or row details)
        if row.get("email") == email or len(res.data) == 1:
            user = row
            break
            
    if not user:
        user = res.data[0]
        
    user_id = user["id"]
    print(f"Using User ID: {user_id}")
    
    # Get user's portfolios
    ports_res = supabase.table("portfolios").select("*").eq("user_id", user_id).execute()
    print("Portfolios found:")
    for p in ports_res.data:
        print(f" - ID: {p['id']}, Name: {p['name']}, Cash: {p.get('cash_balance')}")
        
    if not ports_res.data:
        print("No portfolios found for user!")
        return
        
    portfolio_id = ports_res.data[0]["id"]
    print(f"\nFetching overview for portfolio ID: {portfolio_id}...")
    
    overview = await get_portfolio_overview(user_id, portfolio_id)
    print("\n--- Summary ---")
    summary = overview.get("summary") or {}
    for k, v in summary.items():
        print(f" {k}: {v}")
        
    print("\n--- Positions ---")
    positions = overview.get("positions") or []
    for pos in positions:
        print(f" {pos['ticker']} ({pos.get('name')}): weight={pos.get('weight_pct')}%, cost_basis={pos.get('cost_basis')}, market_value={pos.get('market_value')}, unrealized_pnl={pos.get('unrealized_pnl')}, daily_pnl={pos.get('daily_pnl')}")

if __name__ == "__main__":
    asyncio.run(main())
