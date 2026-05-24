from fastapi import APIRouter, Depends, HTTPException
from typing import List
from schemas.dcf_schema import DCFInput, DCFOutput, DCFSaveRequest, DCFCompareRequest, DCFCompareResponse
from services.dcf_service import dcf_service
from services.pdf_service import generate_dcf_report
from auth import get_current_user
from supabase_client import supabase

import asyncio
from concurrent.futures import ThreadPoolExecutor

router = APIRouter()
executor = ThreadPoolExecutor(max_workers=10)

async def run_calc(dcf_input: DCFInput):
    # Wrap blocking service call in thread to keep gather concurrent
    return await asyncio.to_thread(dcf_service.calculate_intrinsic_value, dcf_input)

@router.post("/export-pdf")
async def export_dcf_pdf(dcf_input: DCFInput, current_user = Depends(get_current_user)):
    """Generate a PDF report for a DCF valuation"""
    try:
        # Calculate valuation first
        valuation = dcf_service.calculate_intrinsic_value(dcf_input)
        
        # Prepare data for PDF
        valuation_data = {
            "ticker": dcf_input.ticker,
            "intrinsic_value": valuation.intrinsic_value_per_share,
            "market_price": valuation.current_market_price,
            "upside_pct": valuation.upside_downside_pct,
            "enterprise_value": valuation.enterprise_value / 1e6, # In Millions
            "wacc": dcf_input.wacc,
            "tgr": dcf_input.terminal_growth_rate,
            "sensitivity_matrix": valuation.sensitivity_matrix
        }
        
        report_id, _ = generate_dcf_report(valuation_data)
        
        return {"report_id": report_id, "download_url": f"/api/v1/report/report/{report_id}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Export error: {str(e)}")

@router.post("/compare", response_model=DCFCompareResponse)
async def compare_dcf(request: DCFCompareRequest, current_user = Depends(get_current_user)):
    """Compare two stocks side-by-side using concurrent calculations"""
    try:
        # Calculate both in parallel
        out_a, out_b = await asyncio.gather(
            run_calc(request.input_a),
            run_calc(request.input_b)
        )
        
        upside_a = out_a.upside_downside_pct or -1.0
        upside_b = out_b.upside_downside_pct or -1.0
        
        diff = abs(upside_a - upside_b)
        
        if abs(upside_a - upside_b) < 0.001:
            winner = "equal"
        elif upside_a > upside_b:
            winner = out_a.ticker
        else:
            winner = out_b.ticker
            
        return DCFCompareResponse(
            winner=winner,
            upside_difference_pct=round(diff * 100, 2),
            output_a=out_a,
            output_b=out_b
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Comparison error: {str(e)}")

@router.post("/calculate", response_model=DCFOutput)
async def calculate_dcf(dcf_input: DCFInput, current_user = Depends(get_current_user)):
    """Calculate DCF valuation based on user inputs"""
    try:
        return dcf_service.calculate_intrinsic_value(dcf_input)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Calculation error: {str(e)}")

@router.post("/save", status_code=201)
async def save_dcf(request: DCFSaveRequest, current_user = Depends(get_current_user)):
    """Save a DCF valuation to history"""
    try:
        data = {
            "user_id": current_user.id,
            "ticker": request.dcf_input.ticker,
            "input_data": request.dcf_input.model_dump(),
            "output_data": request.dcf_output.model_dump()
        }
        response = supabase.table("dcf_valuations").insert(data).execute()
        return {"status": "success", "id": response.data[0]["id"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/history")
async def get_dcf_history(current_user = Depends(get_current_user)):
    """Fetch user's DCF valuation history"""
    try:
        response = supabase.table("dcf_valuations") \
            .select("*") \
            .eq("user_id", current_user.id) \
            .order("created_at", desc=True) \
            .execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.delete("/history/{id}")
async def delete_dcf_history(id: str, current_user = Depends(get_current_user)):
    """Delete a DCF valuation from history"""
    try:
        # Check ownership
        check = supabase.table("dcf_valuations") \
            .select("user_id") \
            .eq("id", id) \
            .single() \
            .execute()
            
        if not check.data:
            raise HTTPException(status_code=404, detail="Valuation not found")
        
        if check.data["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to delete this record")
            
        supabase.table("dcf_valuations").delete().eq("id", id).execute()
        return {"status": "deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/public/{id}")
async def get_public_dcf(id: str):
    """Fetch a public DCF valuation (no auth required)"""
    try:
        response = supabase.table("dcf_valuations") \
            .select("*") \
            .eq("id", id) \
            .eq("is_public", True) \
            .single() \
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Public valuation not found or private")
            
        return response.data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/history/{id}/share")
async def toggle_dcf_share(id: str, is_public: bool, current_user = Depends(get_current_user)):
    """Toggle public visibility of a valuation"""
    try:
        # Check ownership
        check = supabase.table("dcf_valuations") \
            .select("user_id") \
            .eq("id", id) \
            .single() \
            .execute()
            
        if not check.data:
            raise HTTPException(status_code=404, detail="Valuation not found")
        
        if check.data["user_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to modify this record")
            
        response = supabase.table("dcf_valuations") \
            .update({"is_public": is_public}) \
            .eq("id", id) \
            .execute()
            
        return {"status": "success", "is_public": is_public}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
