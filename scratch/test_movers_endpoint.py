import os
import asyncio
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append("backend")

from dotenv import load_dotenv
load_dotenv("backend/.env")

from services.market_data_service import get_movers

async def main():
    print("Fetching movers dynamically...")
    movers = await get_movers()
    print("Movers result:")
    import json
    print(json.dumps(movers, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
