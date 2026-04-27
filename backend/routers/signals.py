from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.signals_service import run_ml_pipeline_stream, scan_market
from dependencies import get_current_user

router = APIRouter()

class PredictRequest(BaseModel):
    ticker: str

@router.post("/predict")
async def predict_signals(
    req: PredictRequest, 
    current_user = Depends(get_current_user)
):
    """
    Stream ML pipeline training and inference progress using Server-Sent Events (SSE).
    """
    return StreamingResponse(run_ml_pipeline_stream(req.ticker, current_user.id), media_type="text/event-stream")

@router.get("/scan")
async def get_market_scan(
    current_user = Depends(get_current_user)
):
    """
    Scan top tickers and return ML-based buy/sell signals.
    """
    try:
        res = await scan_market()
        return res
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
