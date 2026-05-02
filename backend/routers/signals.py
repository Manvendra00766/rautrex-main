from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
import uuid
from services.signals_service import run_signal_pipeline, job_store, scan_market
from dependencies import get_current_user

router = APIRouter()

class PredictRequest(BaseModel):
    ticker: str

@router.post("/predict")
async def predict_signals(
    req: PredictRequest, 
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """
    Start an asynchronous ML pipeline job for the given ticker.
    """
    job_id = str(uuid.uuid4())
    job_store[job_id] = {"status": "processing", "progress": 0, "result": None}
    background_tasks.add_task(run_signal_pipeline, job_id, req.ticker, current_user.id)
    return {"job_id": job_id, "status": "processing"}

@router.get("/status/{job_id}")
async def get_signal_status(job_id: str):
    """
    Poll the status of a signal generation job.
    """
    return job_store.get(job_id, {"status": "not_found"})

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
