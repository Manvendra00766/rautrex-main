from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel
from datetime import datetime, timezone

T = TypeVar('T')

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: Optional[T] = None
    error: Optional[Any] = None
    timestamp: str = datetime.now(timezone.utc).isoformat()

def success_response(data: T) -> ApiResponse[T]:
    return ApiResponse(
        success=True,
        data=data,
        error=None,
        timestamp=datetime.now(timezone.utc).isoformat()
    )

def error_response(error: Any) -> ApiResponse[None]:
    return ApiResponse(
        success=False,
        data=None,
        error=error,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
