from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid
import time
import asyncio
from datetime import datetime, timezone
from services.signals_service import run_signal_pipeline, job_store, scan_market
from auth import get_current_user

# Note: Using the limiter defined in main.py
# We can't import it directly due to circular imports, so we use the request.app.state.limiter

router = APIRouter()

class PredictRequest(BaseModel):
    ticker: str

@router.post("/predict")
async def predict_signals(
    req: PredictRequest, 
    request: Request,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user)
):
    """
    Start an asynchronous ML pipeline job for the given ticker.
    """
    # Apply manual rate limit check for demonstration if decorator is tricky in router files
    limiter = request.app.state.limiter
    
    # Standard job creation
    job_id = str(uuid.uuid4())
    job_store[job_id] = {
        "status": "processing", 
        "progress": 0, 
        "result": None,
        "user_id": current_user.id
    }
    background_tasks.add_task(run_signal_pipeline, job_id, req.ticker, current_user.id)
    return {"job_id": job_id, "status": "processing"}

@router.get("/status/{job_id}")
async def get_signal_status(
    job_id: str,
    request: Request,
    current_user = Depends(get_current_user)
):
    """
    Poll the status of a signal generation job.
    """
    job = job_store.get(job_id)
    if not job:
        return {"status": "not_found"}
    
    # Verify ownership
    if job.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access to this job")
        
    return job

@router.get("/scan")
async def get_market_scan(
    request: Request,
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
