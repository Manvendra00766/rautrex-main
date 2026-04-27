from typing import Dict, Any, List

def validate_financial_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    warnings = []
    
    # Define realistic ranges
    REALISTIC_RANGES = {
        "sharpe": {"min": -2.0, "max": 5.0, "description": "Sharpe Ratio between -2 and 5"},
        "cagr": {"min": -0.5, "max": 1.0, "description": "CAGR between -50% and 100%"},
        "prob_profit": {"min": 0.40, "max": 0.90, "description": "Probability of Profit between 40% and 90%"},
        "max_drawdown": {"min": -1.0, "max": -0.01, "description": "Max Drawdown must be negative and non-zero"}
    }
    
    # Extract common metrics regardless of where they are in the nested dict
    def find_key(d, key):
        if key in d: return d[key]
        for k, v in d.items():
            if isinstance(v, dict):
                res = find_key(v, key)
                if res is not None: return res
        return None

    sharpe = find_key(metrics, "sharpe_ratio")
    if sharpe is None: sharpe = find_key(metrics, "sharpe")
    
    cagr = find_key(metrics, "cagr")
    if cagr is None: cagr = find_key(metrics, "total_return") # fallback check
    
    prob_profit = find_key(metrics, "prob_profit")
    if prob_profit is not None and prob_profit > 1.0: prob_profit /= 100.0 # convert % to decimal if needed for range check
    
    max_dd = find_key(metrics, "max_drawdown")

    report_metrics = {}

    if sharpe is not None:
        report_metrics["sharpe"] = {"value": sharpe, "realistic_range": REALISTIC_RANGES["sharpe"]}
        if sharpe > 5.0:
            warnings.append({"field": "sharpe", "unrealistic_sharpe": True, "note": "Sharpe > 5.0 is highly suspect for real assets"})
            
    if cagr is not None:
        report_metrics["cagr"] = {"value": cagr, "realistic_range": REALISTIC_RANGES["cagr"]}
        if cagr > 1.0: # > 100%
            warnings.append({"field": "cagr", "unrealistic_cagr": True, "note": "CAGR > 100% is extremely rare"})
            
    if prob_profit is not None:
        report_metrics["prob_profit"] = {"value": prob_profit, "realistic_range": REALISTIC_RANGES["prob_profit"]}
        if prob_profit > 0.90:
            warnings.append({"field": "prob_profit", "check_inputs": True, "note": "probability unusually high"})
            
    if max_dd is not None:
        report_metrics["max_drawdown"] = {"value": max_dd, "realistic_range": REALISTIC_RANGES["max_drawdown"]}
        if max_dd == 0.0:
            warnings.append({"field": "max_drawdown", "zero_drawdown_suspect": True, "note": "Zero drawdown on historical data is highly suspect"})
        
    return {
        "is_realistic": len(warnings) == 0,
        "warnings": warnings,
        "metrics_analysis": report_metrics
    }
