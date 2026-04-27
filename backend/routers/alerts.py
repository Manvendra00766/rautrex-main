from fastapi import APIRouter, Depends, HTTPException
from services import alert_service
from pydantic import BaseModel
from dependencies import get_current_user

router = APIRouter(prefix="/api/v1/alerts", tags=["Price Alerts"])

class AlertCreate(BaseModel):
    ticker: str
    condition: str
    target_price: float

@router.post("/")
async def create_new_alert(alert: AlertCreate, current_user = Depends(get_current_user)):
    response = await alert_service.create_alert(current_user.id, alert.ticker, alert.condition, alert.target_price)
    return response.data

@router.get("/")
async def get_my_alerts(current_user = Depends(get_current_user)):
    response = await alert_service.get_user_alerts(current_user.id)
    return response.data

@router.delete("/{alert_id}")
async def delete_user_alert(alert_id: str, current_user = Depends(get_current_user)):
    response = await alert_service.delete_alert(current_user.id, alert_id)
    return {"status": "deleted"}
