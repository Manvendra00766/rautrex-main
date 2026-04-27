from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Any, List
import asyncio
from services.backtester_service import _backtest_sync
from dependencies import get_current_user

router = APIRouter()

class StrategyRequest(BaseModel):
    name: str
    type: str
    params: Dict[str, Any] = Field(default_factory=dict)

class CompareRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    strategies: List[StrategyRequest]
    initial_capital: float = 10000.0

@router.post("/strategies")
async def compare_strategies(
    req: CompareRequest, 
    current_user = Depends(get_current_user)
):
    if len(req.strategies) > 5:
        raise HTTPException(status_code=422, detail="Maximum 5 strategies allowed")
        
    default_params = {
        "sma_crossover": {"fast_period": 50, "slow_period": 200},
        "rsi_reversion": {"rsi_period": 14, "oversold": 30, "overbought": 70},
        "macd": {"fast": 12, "slow": 26, "signal": 9},
        "bollinger": {"period": 20, "std_dev": 2.0},
        "momentum": {"lookback_period": 20}
    }
    
    try:
        loop = asyncio.get_event_loop()
        
        # Always include Buy & Hold baseline by running a dummy backtest if needed
        # or ensuring the benchmark data is fetched.
        # Current implementation relies on gathering tasks.
        
        # If no strategies provided, we should still run at least one to get the benchmark
        # Let's add a dummy if empty to get data, or handle it explicitly.
        
        effective_strategies = req.strategies.copy()
        if not effective_strategies:
            # Add a temporary internal strategy just to get benchmark data
            effective_strategies.append(StrategyRequest(name="_internal_baseline", type="sma_crossover"))

        tasks = []
        for strat in effective_strategies:
            params = strat.params if strat.params else default_params.get(strat.type, {})
            params['percent_equity'] = 1.0
            
            tasks.append(
                loop.run_in_executor(
                    None, 
                    _backtest_sync, 
                    req.ticker, 
                    req.start_date, 
                    req.end_date, 
                    strat.type, 
                    params, 
                    req.initial_capital, 
                    0.1, # commission
                    "percent" # position sizing
                )
            )
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        comparison = {}
        chart_data_combined = {} # date -> { B&H, strat1, strat2... }
        
        for i, res in enumerate(results):
            strat_name = effective_strategies[i].name
            if isinstance(res, Exception):
                print(f"Error in strategy {strat_name}: {res}")
                continue
                
            if strat_name != "_internal_baseline":
                comparison[strat_name] = res['metrics']['strategy']
            
            # Use the first successful run to grab the benchmark
            if "Buy & Hold" not in comparison:
                comparison["Buy & Hold"] = res['metrics']['benchmark']
            
            for pt in res['chart_data']:
                date = pt['time']
                if date not in chart_data_combined:
                    chart_data_combined[date] = {"time": date, "Buy & Hold": pt['bnh_equity']}
                if strat_name != "_internal_baseline":
                    chart_data_combined[date][strat_name] = pt['equity']

        # Format combined chart data
        sorted_dates = sorted(list(chart_data_combined.keys()))
        final_chart_data = [chart_data_combined[d] for d in sorted_dates]
        
        # Calculate winners
        metrics_to_compare = {
            "total_return": "max",
            "cagr": "max",
            "sharpe_ratio": "max",
            "sortino_ratio": "max",
            "max_drawdown": "max", # Since it's negative, closer to 0 is max
            "win_rate": "max",
            "profit_factor": "max"
        }
        
        winners = {}
        for metric, criteria in metrics_to_compare.items():
            best_strat = None
            best_val = None
            for strat_name, strat_metrics in comparison.items():
                val = strat_metrics.get(metric)
                # Fallback for comparison if None
                comp_val = val if val is not None else -float('inf')
                
                if best_strat is None:
                    best_val = comp_val
                    best_strat = strat_name
                elif criteria == "max" and comp_val > best_val:
                    best_val = comp_val
                    best_strat = strat_name
                elif criteria == "min" and comp_val < best_val:
                    best_val = comp_val
                    best_strat = strat_name
            winners[metric] = best_strat
            
        return {
            "metrics": comparison,
            "chart_data": final_chart_data,
            "winners": winners
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
