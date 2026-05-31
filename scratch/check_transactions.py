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

# Fetch transactions
portfolio_id = "4d85788c-9016-41fe-aa44-c48b42d5cb98"
try:
    print(f"--- TRANSACTIONS FOR PORTFOLIO {portfolio_id} ---")
    tx_res = supabase.table("transactions").select("*").eq("portfolio_id", portfolio_id).execute()
    print(f"Total transactions found: {len(tx_res.data)}")
    for tx in tx_res.data[:10]:
        print(f"  ID: {tx['id']} | Type: {tx['transaction_type']} | Symbol: {tx.get('symbol')} | Qty: {tx.get('quantity')} | Price: {tx.get('price')}")
except Exception as e:
    print(f"Error: {e}")
