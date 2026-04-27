import numpy as np
import pandas as pd
from typing import Any

def clean_nans(obj: Any) -> Any:
    """
    Recursively replaces NaN and Inf values with None (JSON null) to ensure JSON compliance.
    Handles nested dicts, lists, numpy types, and pandas objects.
    """
    if obj is None:
        return None
        
    if isinstance(obj, dict):
        return {k: clean_nans(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nans(x) for x in obj]
    elif isinstance(obj, (float, np.float32, np.float64)):
        if np.isnan(obj) or np.isinf(obj):
            return 0.0 # Return 0.0 instead of None for financial metrics usually
        return float(obj)
    elif isinstance(obj, (int, np.int32, np.int64)):
        return int(obj)
    elif isinstance(obj, np.ndarray):
        return [clean_nans(x) for x in obj.tolist()]
    elif isinstance(obj, (pd.Series, pd.DataFrame)):
        return clean_nans(obj.to_dict('records')) if isinstance(obj, pd.DataFrame) else clean_nans(obj.to_dict())
    elif hasattr(obj, 'item'): # Handle other numpy scalars
        try:
            val = obj.item()
            return clean_nans(val)
        except:
            return str(obj)
            
    return obj
