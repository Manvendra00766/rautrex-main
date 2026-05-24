from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from auth import get_current_user
from services.report_service import report_service
from services import db_service
from core.logger import logger
import os
import asyncio

router = APIRouter(prefix="/api/v1/report", tags=["Reports"])

def cleanup_file(path: str):
    """Cleanup file after a delay to ensure transfer is complete"""
    def _do_remove():
        import time
        time.sleep(60) # Longer wait for safety
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"Cleanup: removed {path}")
            except Exception as e:
                print(f"Cleanup error: {e}")
    
    import threading
    threading.Thread(target=_do_remove, daemon=True).start()

@router.get("/health")
async def report_health():
    return {"status": "ok", "router": "report"}

@router.get("/report/{report_id}")
async def get_report(request: Request, report_id: str, background_tasks: BackgroundTasks, user = Depends(get_current_user)):
    auth_header = request.headers.get('Authorization', 'MISSING')
    logger.info(f"Report Access: {report_id} | Auth: {auth_header[:20]}...")
    
    # Absolute path matching the service
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(base_dir, "tmp", f"rautrex_report_{report_id}.pdf")
    
    if not os.path.exists(filepath):
        logger.error(f"Report file not found at {filepath}")
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Use BackgroundTask for cleanup
    background_tasks.add_task(cleanup_file, filepath)
    
    return FileResponse(
        path=filepath,
        media_type="application/pdf",
        filename=f"rautrex_report_{report_id}.pdf"
    )

@router.get("/export/{portfolio_id}")
async def export_portfolio_report(portfolio_id: str, current_user = Depends(get_current_user)):
    """Generate and download a comprehensive PDF report for a portfolio"""
    try:
        # 1. Gather Data
        data = await report_service.gather_report_data(portfolio_id, current_user.id)
        
        if not data:
            # Check if portfolio exists at all to distinguish 404 from 403
            exists = await db_service.get_portfolio_by_id(portfolio_id)
            if not exists:
                raise HTTPException(status_code=404, detail="Portfolio not found")
            else:
                raise HTTPException(status_code=403, detail="Not authorized to access this portfolio")
        
        # 2. Build PDF
        pdf_buffer = report_service.build_pdf(data)
        
        # 3. Stream Response
        filename = f"rautrex_report_{portfolio_id}.pdf"
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers=headers
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF Export Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
