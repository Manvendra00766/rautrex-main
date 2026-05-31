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

portfolio_id = "4d85788c-9016-41fe-aa44-c48b42d5cb98"
try:
    p_res = supabase.table("portfolios").select("*").eq("id", portfolio_id).execute()
    if p_res.data:
        p = p_res.data[0]
        print(f"user_id: {p.get('user_id')}")
except Exception as e:
    print(f"Error: {e}")
