import numpy as np
import pandas as pd
from typing import Any, List, Dict
import math
import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)

from decimal import Decimal

def safe_json(obj: Any, seen=None) -> Any:
    """
    Recursively replaces NaN and Inf values with 0 (JSON safe).
    Rules:
    - np.nan -> 0
    - np.inf -> 0
    - -np.inf -> 0
    - numpy.float64 -> float()
    - numpy.int64 -> int()
    - Decimal -> float()
    - pandas NaT -> None
    - recursively clean dict/list
    """
    if obj is None:
        return None
        
    if seen is None:
        seen = set()
        
    # Prevent circular references
    obj_id = id(obj)
    if obj_id in seen:
        return None
    
    if isinstance(obj, (dict, list)):
        seen.add(obj_id)

    if isinstance(obj, dict):
        return {str(k): safe_json(v, seen) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_json(x, seen) for x in obj]
    elif isinstance(obj, (float, np.floating)):
        if math.isnan(obj) or math.isinf(obj):
            logger.warning("NaN or Inf detected and replaced with 0.0")
            print("NaN detected in portfolio response")
            return 0.0
        return float(obj)
    elif isinstance(obj, (int, np.integer)):
        return int(obj)
    elif isinstance(obj, (bool, np.bool_)):
        return bool(obj)
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, (str, bytes)):
        return str(obj)
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif pd.isna(obj) and not isinstance(obj, (str, bytes)):
        # Handles NaT and other pd.NA types
        return None
    elif isinstance(obj, np.ndarray):
        return [safe_json(x, seen) for x in obj.tolist()]
    elif isinstance(obj, (pd.Series, pd.DataFrame)):
        return safe_json(obj.to_dict('records') if isinstance(obj, pd.DataFrame) else obj.to_dict(), seen)
    elif hasattr(obj, 'item') and callable(getattr(obj, 'item')):
        try:
            return safe_json(obj.item(), seen)
        except Exception:
            return str(obj)
            
    return str(obj) if obj is not None else None


def normalize_history(history: List[Any]) -> List[Dict[str, Any]]:
    """
    Normalizes a history list where items might be tuples (date, value) or dicts.
    Returns a standardized list of dicts: [{"date": "YYYY-MM-DD", "nav": value}, ...]
    Skips invalid rows safely. Rejects complex objects like tuples/lists used as dates.
    """
    normalized = []
    if not isinstance(history, list):
        return normalized

    for item in history:
        try:
            if isinstance(item, tuple) and len(item) == 2:
                raw_date, nav_val = item
                
                # REJECT if raw_date is not a "date-like" string or object
                if isinstance(raw_date, (list, tuple, dict)):
                    continue
                    
                date_val = pd.to_datetime(raw_date, errors='coerce', format='ISO8601')
                if date_val is None or pd.isna(date_val) or isinstance(date_val, (pd.Index, pd.Series, np.ndarray)):
                    continue
                    
                normalized.append({
                    "date": date_val.strftime('%Y-%m-%d'),
                    "nav": float(nav_val)
                })
            elif isinstance(item, dict):
                raw_date = item.get("date") or item.get("snapshot_date")
                nav_val = item.get("nav") or item.get("value") or 0.0
                
                if isinstance(raw_date, (list, tuple, dict)):
                    continue
                    
                date_val = pd.to_datetime(raw_date, errors='coerce', format='ISO8601')
                if date_val is None or pd.isna(date_val) or isinstance(date_val, (pd.Index, pd.Series, np.ndarray)):
                    continue
                    
                new_item = dict(item)
                new_item["date"] = date_val.strftime('%Y-%m-%d')
                new_item["nav"] = float(nav_val)
                normalized.append(new_item)
        except Exception:
            # Silent skip for invalid data during normalization
            continue

    return normalized
