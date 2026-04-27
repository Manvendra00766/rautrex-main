from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from services.validation_service import validate_financial_metrics

router = APIRouter()

@router.post("/sanity")
async def validate_sanity(metrics: Dict[str, Any]):
    """
    Accepts any set of financial metrics and returns a validation report 
    with realistic range checks for each metric.
    """
    try:
        validation_report = validate_financial_metrics(metrics)
        return validation_report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
