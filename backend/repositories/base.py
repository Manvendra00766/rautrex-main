from typing import TypeVar, Generic, Type, Any, Optional, List, Dict
from pydantic import BaseModel
from core.logger import logger
from core.exceptions import AppError

# Import mapped SQLAlchemy models
from models.user_data import (
    User,
    UserPortfolio,
    PortfolioPosition,
    Watchlist,
    WatchlistItem,
    SavedBacktest,
    SavedSignal,
    SavedSimulation,
    Notification,
    PriceAlert,
    CompanyTickerMapping,
    PortfolioMetricsCache,
    Instrument
)

# Map table name strings to modern, high-performance SQLAlchemy models
TABLE_MODEL_MAP = {
    "users": User,
    "portfolios": UserPortfolio,
    "user_portfolios": UserPortfolio,
    "portfolio_positions": PortfolioPosition,
    "watchlists": Watchlist,
    "watchlist_items": WatchlistItem,
    "saved_backtests": SavedBacktest,
    "saved_signals": SavedSignal,
    "saved_simulations": SavedSimulation,
    "notifications": Notification,
    "price_alerts": PriceAlert,
    "company_ticker_mappings": CompanyTickerMapping,
    "portfolio_metrics_cache": PortfolioMetricsCache,
    "instruments": Instrument
}

T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T]):
    def __init__(self, table_name: str, model_class: Type[T]):
        self.table_name = table_name
        self.model_class = model_class
        self.db_model = TABLE_MODEL_MAP.get(table_name)
        if not self.db_model:
            raise ValueError(f"No SQLAlchemy model registered for table: {table_name}")

    def _to_pydantic(self, obj) -> T:
        """Safely convert a SQLAlchemy database object to its corresponding Pydantic schema,
        handling missing virtual/derived columns or schema mismatch gracefully.
        """
        data = {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
        
        # Fill in defaults for fields required by the Pydantic schema but not present in database columns
        for field_name, field_info in self.model_class.model_fields.items():
            if field_name not in data or data[field_name] is None:
                default_val = getattr(field_info, 'default', None)
                from pydantic_core import PydanticUndefined
                if default_val is not PydanticUndefined and default_val is not None:
                    data[field_name] = default_val
                else:
                    # Provide appropriate safe fallback values based on the field annotation
                    annotation = getattr(field_info, 'annotation', None)
                    if annotation == float:
                        data[field_name] = 0.0
                    elif annotation == int:
                        data[field_name] = 0
                    elif annotation == str:
                        data[field_name] = ""
                    else:
                        data[field_name] = None
            else:
                # Coerce data types to match target Pydantic schema annotations perfectly
                annotation = getattr(field_info, 'annotation', None)
                val = data[field_name]
                if annotation == str and not isinstance(val, str):
                    data[field_name] = str(val)
                elif annotation == float and not isinstance(val, float):
                    try:
                        data[field_name] = float(val)
                    except (ValueError, TypeError):
                        pass
                elif annotation == int and not isinstance(val, int):
                    try:
                        data[field_name] = int(val)
                    except (ValueError, TypeError):
                        pass
        return self.model_class(**data)

    async def get_by_id(self, id: str) -> Optional[T]:
        """Fetch a single record by its ID using modern, non-blocking native async database sessions."""
        try:
            from database.connection import AsyncSessionLocal
            from sqlalchemy.future import select
            
            try:
                python_type = getattr(self.db_model.id.type, 'python_type', None)
                lookup_id = int(id) if python_type == int else id
            except (ValueError, TypeError):
                lookup_id = id

            async with AsyncSessionLocal() as session:
                stmt = select(self.db_model).where(self.db_model.id == lookup_id)
                res = await session.execute(stmt)
                obj = res.scalar_one_or_none()
                if obj:
                    return self._to_pydantic(obj)
                return None
        except Exception as e:
            logger.error(f"Error fetching from {self.table_name} by id {id}: {e}")
            raise AppError(f"Database fetch failed", status_code=500)

    async def get_all(self, filters: Optional[Dict[str, Any]] = None) -> List[T]:
        """Fetch all records matching filters asynchronously and return typed Pydantic models."""
        try:
            from database.connection import AsyncSessionLocal
            from sqlalchemy.future import select
            
            async with AsyncSessionLocal() as session:
                stmt = select(self.db_model)
                if filters:
                    for k, v in filters.items():
                        column = getattr(self.db_model, k, None)
                        if column is not None:
                            stmt = stmt.where(column == v)
                
                res = await session.execute(stmt)
                results = res.scalars().all()
                return [self._to_pydantic(obj) for obj in results]
        except Exception as e:
            logger.error(f"Error fetching all from {self.table_name}: {e}")
            raise AppError(f"Database fetch failed", status_code=500)

    async def create(self, data: T) -> T:
        """Create a new database record asynchronously, filtering for columns that exist in the database table."""
        try:
            from database.connection import AsyncSessionLocal
            
            dump = data.model_dump(exclude_unset=True)
            
            # Identify columns that actually exist in the database table
            columns = {c.key for c in self.db_model.__table__.columns}
            filtered_dump = {k: v for k, v in dump.items() if k in columns}
            
            # Coerce types to map Pydantic representations perfectly to SQLAlchemy types
            for k in list(filtered_dump.keys()):
                column = getattr(self.db_model, k, None)
                if column is not None:
                    python_type = getattr(column.type, 'python_type', None)
                    if python_type == int and filtered_dump[k] is not None:
                        try:
                            filtered_dump[k] = int(filtered_dump[k])
                        except ValueError:
                            pass
                    elif python_type == str and filtered_dump[k] is not None:
                        filtered_dump[k] = str(filtered_dump[k])
            
            db_obj = self.db_model(**filtered_dump)
            
            async with AsyncSessionLocal() as session:
                session.add(db_obj)
                await session.commit()
                await session.refresh(db_obj)
                return self._to_pydantic(db_obj)
        except Exception as e:
            logger.error(f"Error creating in {self.table_name}: {e}")
            raise AppError(f"Database insert failed", status_code=500)

    async def update(self, id: str, data: Dict[str, Any]) -> T:
        """Update a record atomically inside an async transaction block, filtering for table columns."""
        try:
            from database.connection import AsyncSessionLocal
            from sqlalchemy.future import select
            
            try:
                python_type = getattr(self.db_model.id.type, 'python_type', None)
                lookup_id = int(id) if python_type == int else id
            except (ValueError, TypeError):
                lookup_id = id
                
            async with AsyncSessionLocal() as session:
                stmt = select(self.db_model).where(self.db_model.id == lookup_id)
                res = await session.execute(stmt)
                obj = res.scalar_one_or_none()
                if not obj:
                    raise AppError("Record not found", status_code=404)
                
                # Apply fields updating only for columns that exist in the database table
                columns = {c.key for c in self.db_model.__table__.columns}
                for k, v in data.items():
                    if k in columns:
                        column = getattr(self.db_model, k, None)
                        if column is not None:
                            python_type = getattr(column.type, 'python_type', None)
                            if python_type == int and v is not None:
                                try:
                                    v = int(v)
                                except ValueError:
                                    pass
                            elif python_type == str and v is not None:
                                v = str(v)
                            setattr(obj, k, v)
                
                await session.commit()
                await session.refresh(obj)
                return self._to_pydantic(obj)
        except AppError:
            raise
        except Exception as e:
            logger.error(f"Error updating {self.table_name} id {id}: {e}")
            raise AppError(f"Database update failed", status_code=500)

    async def delete(self, id: str) -> bool:
        """Atomically delete a record asynchronously using SQLAlchemy sessions."""
        try:
            from database.connection import AsyncSessionLocal
            from sqlalchemy.future import select
            
            try:
                python_type = getattr(self.db_model.id.type, 'python_type', None)
                lookup_id = int(id) if python_type == int else id
            except (ValueError, TypeError):
                lookup_id = id
                
            async with AsyncSessionLocal() as session:
                stmt = select(self.db_model).where(self.db_model.id == lookup_id)
                res = await session.execute(stmt)
                obj = res.scalar_one_or_none()
                if obj:
                    await session.delete(obj)
                    await session.commit()
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting from {self.table_name} id {id}: {e}")
            return False
