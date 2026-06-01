import asyncio
import os
import sys
sys.path.append(os.path.join(os.getcwd(), "backend"))
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_KEY"] = "mock"
from services.portfolio_service import _get_returns_async
async def test():
    returns = await _get_returns_async(["718GS2033.NS"])
    print("Empty:", returns.empty)
    print("Len:", len(returns))
asyncio.run(test())
