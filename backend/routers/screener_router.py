from fastapi import APIRouter, Depends, HTTPException
from typing import List
from schemas.screener_schema import ScreenerRequest, ScreenerResult, ScreenerFilter, ScreenerPreset, ScreenerFilterRequest, ScreenerStockResult
from services.screener_service import screener_service
from auth import get_current_user
from supabase_client import supabase
from pydantic import BaseModel
from core.logger import logger

from infrastructure.redis_client import redis_client

router = APIRouter(tags=["Screener"])

class PresetCreate(BaseModel):
    name: str
    filters: List[ScreenerFilter]

@router.post("/filter")
async def filter_stocks(filters: ScreenerFilterRequest, current_user = Depends(get_current_user)):
    """Run stock screener with specific filters"""
    try:
        return await screener_service.run_filter(filters)
    except Exception as e:
        logger.error(f"Screener filter error: {e}")
        raise HTTPException(status_code=503, detail="Market data service unavailable")

@router.delete("/cache")
async def clear_screener_cache(current_user = Depends(get_current_user)):
    """Flush all screener-related keys from Redis"""
    try:
        # This is a bit brute-force for Redis but effective for our prefix
        keys = await redis_client.redis.keys("screener:*")
        if keys:
            await redis_client.redis.delete(*keys)
        return {"status": "success", "cleared_keys": len(keys)}
    except Exception as e:
        logger.error(f"Cache clear error: {e}")
        return {"status": "error", "detail": str(e)}

@router.post("/run", response_model=List[ScreenerResult])
async def run_screener(request: ScreenerRequest, current_user = Depends(get_current_user)):
    """Run the stock screener with filters"""
    try:
        return await screener_service.run_screener(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Screener error: {str(e)}")

@router.get("/presets", response_model=List[ScreenerPreset])
async def get_presets(current_user = Depends(get_current_user)):
    """Fetch all saved presets for the current user"""
    try:
        response = supabase.table("screener_presets") \
            .select("*") \
            .eq("user_id", current_user.id) \
            .order("created_at", desc=True) \
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/presets", response_model=ScreenerPreset)
async def save_preset(preset: PresetCreate, current_user = Depends(get_current_user)):
    """Save a new screener preset"""
    try:
        data = {
            "user_id": current_user.id,
            "name": preset.name,
            "filters": [f.model_dump() for f in preset.filters]
        }
        response = supabase.table("screener_presets").insert(data).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to save preset")
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/presets/{id}")
async def delete_preset(id: str, current_user = Depends(get_current_user)):
    """Delete a screener preset if owned by the user"""
    try:
        # Check ownership
        check = supabase.table("screener_presets") \
            .select("user_id") \
            .eq("id", id) \
            .single() \
            .execute()
        
        if not check.data:
            raise HTTPException(status_code=404, detail="Preset not found")
        
        if check.data["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this preset")
        
        supabase.table("screener_presets").delete().eq("id", id).execute()
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# SQL Schema for Supabase:
"""
CREATE TABLE screener_presets (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid REFERENCES auth.users(id) NOT NULL,
    name text NOT NULL,
    filters jsonb NOT NULL,
    created_at timestamptz DEFAULT now()
);

ALTER TABLE screener_presets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can only access their own presets" 
ON screener_presets FOR ALL 
USING (auth.uid() = user_id);
"""
