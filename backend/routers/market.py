from fastapi import APIRouter, HTTPException
from services.market_data_service import get_indices, get_movers, run_screener

router = APIRouter()

@router.get("/indices")
async def fetch_indices():
    try:
        data = await get_indices()
        return {"indices": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/movers")
async def fetch_movers():
    try:
        data = await get_movers()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/screener")
async def fetch_screener():
    try:
        data = await run_screener()
        return {"results": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))