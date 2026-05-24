
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Try to find .env in backend or current dir
load_dotenv("backend/.env")
load_dotenv(".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
# Check multiple possible keys
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

print(f"DEBUG: URL={SUPABASE_URL}")
print(f"DEBUG: KEY={'Found' if SUPABASE_KEY else 'Missing'}")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Missing Supabase configuration.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

try:
    print(f"Checking for 'dcf_valuations' table at {SUPABASE_URL}...")
    response = supabase.table("dcf_valuations").select("id").limit(1).execute()
    print("Success: Table exists.")
except Exception as e:
    err_str = str(e)
    print(f"Error: {err_str}")
    if "PGRST205" in err_str or "404" in err_str:
        print("\nTable 'dcf_valuations' appears to be missing.")
        print("Please run the following SQL in your Supabase SQL Editor:\n")
        
        with open("supabase/migrations/20240508_add_dcf_module.sql", "r") as f:
            print(f.read())
            
        print("\nThen run this for sharing support:\n")
        with open("supabase/migrations/20240508_add_dcf_sharing.sql", "r") as f:
            print(f.read())
