from fastapi import APIRouter, Depends, HTTPException
from services import notification_service
from supabase_client import supabase
from dependencies import get_current_user

import traceback

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])

@router.get("/")
async def get_my_notifications(limit: int = 50, offset: int = 0, current_user = Depends(get_current_user)):
    try:
        response = await notification_service.get_notifications(current_user.id, limit, offset)
        return response.data
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/unread-count")
async def get_my_unread_count(current_user = Depends(get_current_user)):
    try:
        count = await notification_service.get_unread_count(current_user.id)
        return {"unread_count": count}
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{id}/read")
async def mark_notification_read(id: str, current_user = Depends(get_current_user)):
    try:
        response = await notification_service.mark_read(current_user.id, id)
        return response.data
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/read-all")
async def mark_notifications_all_read(current_user = Depends(get_current_user)):
    try:
        response = await notification_service.mark_all_read(current_user.id)
        return response.data
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id}")
async def delete_notification(id: str, current_user = Depends(get_current_user)):
    try:
        response = supabase.table("notifications").delete().eq("id", id).eq("user_id", current_user.id).execute()
        return response.data
    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
