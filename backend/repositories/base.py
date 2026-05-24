from typing import TypeVar, Generic, Type, Any, Optional, List, Dict
from pydantic import BaseModel
from supabase_client import supabase
from core.logger import logger
from core.exceptions import AppError

T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T]):
    def __init__(self, table_name: str, model_class: Type[T]):
        self.table_name = table_name
        self.model_class = model_class

    async def get_by_id(self, id: str) -> Optional[T]:
        try:
            # Note: supabase-py is synchronous under the hood, but in FastAPI it's better to run in thread pool if blocking
            # Or use postgrest-py async client. Assuming standard synchronous supabase python client wrapped in async.
            import asyncio
            response = await asyncio.to_thread(
                lambda: supabase.table(self.table_name).select("*").eq("id", id).execute()
            )
            data = response.data
            if data:
                return self.model_class(**data[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching from {self.table_name} by id {id}: {e}")
            raise AppError(f"Database fetch failed", status_code=500)

    async def get_all(self, filters: Optional[Dict[str, Any]] = None) -> List[T]:
        try:
            import asyncio
            query = supabase.table(self.table_name).select("*")
            if filters:
                for k, v in filters.items():
                    query = query.eq(k, v)
            
            response = await asyncio.to_thread(lambda: query.execute())
            return [self.model_class(**item) for item in response.data]
        except Exception as e:
            logger.error(f"Error fetching all from {self.table_name}: {e}")
            raise AppError(f"Database fetch failed", status_code=500)

    async def create(self, data: T) -> T:
        try:
            import asyncio
            response = await asyncio.to_thread(
                lambda: supabase.table(self.table_name).insert(data.model_dump(exclude_unset=True)).execute()
            )
            if response.data:
                return self.model_class(**response.data[0])
            raise AppError("Failed to create record")
        except Exception as e:
            logger.error(f"Error creating in {self.table_name}: {e}")
            raise AppError(f"Database insert failed", status_code=500)

    async def update(self, id: str, data: Dict[str, Any]) -> T:
        try:
            import asyncio
            response = await asyncio.to_thread(
                lambda: supabase.table(self.table_name).update(data).eq("id", id).execute()
            )
            if response.data:
                return self.model_class(**response.data[0])
            raise AppError("Failed to update record")
        except Exception as e:
            logger.error(f"Error updating {self.table_name} id {id}: {e}")
            raise AppError(f"Database update failed", status_code=500)

    async def delete(self, id: str) -> bool:
        try:
            import asyncio
            await asyncio.to_thread(
                lambda: supabase.table(self.table_name).delete().eq("id", id).execute()
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting from {self.table_name} id {id}: {e}")
            return False
