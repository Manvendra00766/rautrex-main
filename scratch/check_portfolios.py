import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv("backend/.env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Missing Supabase config.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. Fetch portfolios
try:
    print("--- PORTFOLIOS ---")
    p_res = supabase.table("portfolios").select("*").execute()
    for p in p_res.data:
        print(f"ID: {p['id']} | Name: {p['name']} | Strategy: {p.get('strategy')} | Cash: {p.get('cash_balance')}")
        
        # Fetch positions for this portfolio
        pos_res = supabase.table("portfolio_positions").select("*").eq("portfolio_id", p["id"]).execute()
        print("  Positions:")
        for pos in pos_res.data:
            print(f"    Ticker: {pos['ticker']} | Shares: {pos['shares']} | Avg Cost: {pos.get('avg_cost_price')}")
except Exception as e:
    print(f"Error: {e}")
