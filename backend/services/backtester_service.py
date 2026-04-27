import pandas as pd
import numpy as np
import yfinance as yf
import asyncio
from typing import Dict, Any, List
import math
from utils import clean_nans

def calculate_drawdown(equity_curve: pd.Series) -> pd.Series:
    if equity_curve.empty:
        return pd.Series()
    rolling_max = equity_curve.cummax()
    drawdown = equity_curve / rolling_max - 1.0
    return drawdown

def calculate_metrics(equity_curve: pd.Series, initial_capital: float, risk_free_rate: float = 0.02) -> Dict[str, float]:
    if equity_curve.empty:
        return {}
        
    returns = equity_curve.pct_change().dropna()
    total_return = (equity_curve.iloc[-1] / initial_capital) - 1.0 if initial_capital > 0 else 0
    
    if len(equity_curve) > 1:
        days = (equity_curve.index[-1] - equity_curve.index[0]).days
        years = days / 365.25 if days > 0 else 1
    else:
        years = 1
        
    cagr = (equity_curve.iloc[-1] / initial_capital) ** (1 / years) - 1.0 if years > 0 and (equity_curve.iloc[-1] / initial_capital) > 0 else 0
    
    annualized_volatility = returns.std() * np.sqrt(252) if not returns.empty else 0
    sharpe_ratio = (cagr - risk_free_rate) / annualized_volatility if annualized_volatility > 1e-9 else 0
    
    negative_returns = returns[returns < 0]
    downside_deviation = negative_returns.std() * np.sqrt(252) if not negative_returns.empty else 0
    sortino_ratio = (cagr - risk_free_rate) / downside_deviation if downside_deviation > 1e-9 else 0
    
    drawdown = calculate_drawdown(equity_curve)
    max_drawdown = drawdown.min() if not drawdown.empty else 0
    
    calmar_ratio = cagr / abs(max_drawdown) if max_drawdown < -1e-9 else 0
    
    squared_drawdowns = drawdown ** 2
    ulcer_index = np.sqrt(squared_drawdowns.mean()) * 100 if len(squared_drawdowns) > 0 else 0
    
    recovery_factor = total_return / abs(max_drawdown) if max_drawdown < -1e-9 else (total_return if total_return > 0 else 0)

    return {
        "total_return": float(total_return),
        "cagr": float(cagr),
        "sharpe_ratio": float(sharpe_ratio),
        "sortino_ratio": float(sortino_ratio),
        "max_drawdown": float(max_drawdown),
        "calmar_ratio": float(calmar_ratio),
        "annualized_volatility": float(annualized_volatility),
        "ulcer_index": float(ulcer_index),
        "recovery_factor": float(recovery_factor)
    }

from services.notification_service import create_notification

async def run_backtest_logic(
    ticker: str,
    start_date: str,
    end_date: str,
    strategy_type: str,
    strategy_params: Dict[str, Any],
    initial_capital: float,
    commission: float,
    position_sizing: str,
    user_id: str
):
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, _backtest_sync, ticker, start_date, end_date, strategy_type, strategy_params, initial_capital, commission, position_sizing)
    
    # Create notification
    try:
        total_return = results['metrics']['strategy']['total_return'] * 100
        await create_notification(
            user_id=user_id,
            type="backtest_complete",
            title=f"Backtest Complete: {ticker}",
            body=f"Strategy {strategy_type} finished with {round(total_return, 2)}% total return.",
            metadata={"ticker": ticker, "strategy": strategy_type, "total_return": total_return}
        )
    except Exception as e:
        print(f"Failed to create backtest notification: {e}")
        
    return results

def _backtest_sync(ticker, start_date, end_date, strategy_type, strategy_params, initial_capital, commission, position_sizing):
    # Auto-fetch benchmark
    benchmark_ticker = '^NSEI' if ticker.endswith('.NS') else '^GSPC'
    
    try:
        data = yf.download([ticker, benchmark_ticker], start=start_date, end=end_date, group_by='ticker', progress=False)
        
        if isinstance(data.columns, pd.MultiIndex):
            if ticker in data.columns.levels[0]:
                df = data[ticker].copy()
            else:
                df = yf.download(ticker, start=start_date, end=end_date, progress=False).copy()
                
            if benchmark_ticker in data.columns.levels[0]:
                bench_df = data[benchmark_ticker].copy()
            else:
                bench_df = pd.DataFrame(index=df.index)
                bench_df['Close'] = 1.0
        else:
            df = data.copy()
            bench_df = pd.DataFrame(index=df.index)
            bench_df['Close'] = 1.0
            
    except Exception as e:
        print(f"Data download error: {e}")
        df = yf.download(ticker, start=start_date, end=end_date, progress=False).copy()
        bench_df = pd.DataFrame(index=df.index)
        bench_df['Close'] = 1.0

    if df.empty:
        raise ValueError(f"No data found for {ticker} between {start_date} and {end_date}")
        
    df.dropna(subset=['Close'], inplace=True)
    for col in ['Open', 'High', 'Low']:
        if col not in df.columns: df[col] = df['Close']
    
    bench_df.dropna(subset=['Close'], inplace=True)
    
    commission_rate = commission / 100.0
    slippage_rate = strategy_params.get('slippage_rate', 0.0005)
    spread_rate = strategy_params.get('spread_rate', 0.0005)
    cost_per_side = commission_rate + slippage_rate + spread_rate
    
    df['Signal'] = 0
    if strategy_type == 'sma_crossover':
        fast = strategy_params.get('fast_period', 50)
        slow = strategy_params.get('slow_period', 200)
        df['Fast_SMA'] = df['Close'].rolling(window=fast).mean()
        df['Slow_SMA'] = df['Close'].rolling(window=slow).mean()
        df['Signal'] = np.where(df['Fast_SMA'] > df['Slow_SMA'], 1, 0)
        
    elif strategy_type == 'rsi_reversion':
        period = strategy_params.get('rsi_period', 14)
        oversold = strategy_params.get('oversold', 30)
        overbought = strategy_params.get('overbought', 70)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        # Avoid division by zero
        rs = gain / loss.replace(0, np.nan)
        df['RSI'] = 100 - (100 / (1 + rs.fillna(0)))
        
        rsi_signal = np.zeros(len(df))
        in_pos = False
        for i in range(len(df)):
            rsi = df['RSI'].iloc[i]
            if not in_pos and rsi < oversold:
                in_pos = True
            elif in_pos and rsi > overbought:
                in_pos = False
            rsi_signal[i] = 1 if in_pos else 0
        df['Signal'] = rsi_signal
        
    elif strategy_type == 'macd':
        fast = strategy_params.get('fast', 12)
        slow = strategy_params.get('slow', 26)
        signal = strategy_params.get('signal', 9)
        exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['Close'].ewm(span=slow, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal_Line'] = df['MACD'].ewm(span=signal, adjust=False).mean()
        df['Signal'] = np.where(df['MACD'] > df['Signal_Line'], 1, 0)
        
    elif strategy_type == 'bollinger':
        period = strategy_params.get('period', 20)
        std_dev = strategy_params.get('std_dev', 2.0)
        df['SMA'] = df['Close'].rolling(window=period).mean()
        df['STD'] = df['Close'].rolling(window=period).std()
        df['Upper'] = df['SMA'] + (df['STD'] * std_dev)
        df['Lower'] = df['SMA'] - (df['STD'] * std_dev)
        
        bb_signal = np.zeros(len(df))
        in_pos = False
        for i in range(len(df)):
            close = df['Close'].iloc[i]
            lower = df['Lower'].iloc[i]
            upper = df['Upper'].iloc[i]
            if not in_pos and close < lower:
                in_pos = True
            elif in_pos and close > upper:
                in_pos = False
            bb_signal[i] = 1 if in_pos else 0
        df['Signal'] = bb_signal
        
    elif strategy_type == 'momentum':
        lookback = strategy_params.get('lookback_period', 20)
        df['Momentum'] = df['Close'].pct_change(periods=lookback)
        df['Signal'] = np.where(df['Momentum'] > 0, 1, 0)
        
    stop_loss_pct = strategy_params.get('stop_loss_pct', None)
    take_profit_pct = strategy_params.get('take_profit_pct', None)
    
    trades_log = []
    equity_curve = []
    
    current_capital = initial_capital
    position = 0
    entry_price = 0.0
    entry_date = None
    trade_id_counter = 1
    
    dates = df.index
    closes = df['Close'].values
    opens = df['Open'].values
    highs = df['High'].values
    lows = df['Low'].values
    signals = df['Signal'].values
    
    last_20_trades_pnl = []
    
    for i in range(len(df)):
        date = dates[i]
        
        if i > 0:
            yesterday_signal = signals[i-1]
            if position == 0 and yesterday_signal == 1:
                entry_price = opens[i]
                entry_price_gross = entry_price * (1 + cost_per_side)
                
                if position_sizing == 'fixed':
                    fixed_amount = strategy_params.get('fixed_amount', 1000)
                    alloc_capital = min(fixed_amount, current_capital)
                elif position_sizing == 'kelly':
                    if len(last_20_trades_pnl) > 0:
                        wins = [x for x in last_20_trades_pnl if x > 0]
                        losses = [x for x in last_20_trades_pnl if x <= 0]
                        win_rate_kelly = len(wins) / len(last_20_trades_pnl)
                        avg_win_kelly = np.mean(wins) if wins else 0
                        avg_loss_kelly = abs(np.mean(losses)) if losses else 1e-5
                        b = avg_win_kelly / avg_loss_kelly if avg_loss_kelly > 0 else 1.0
                        f_star = (win_rate_kelly * (b + 1) - 1) / b if b > 0 else 0
                        f_star = max(0.0, min(0.25, f_star))
                    else:
                        f_star = 0.1
                    alloc_capital = current_capital * f_star
                else:
                    pct = strategy_params.get('percent_equity', 1.0)
                    alloc_capital = current_capital * pct
                
                if alloc_capital > 0:
                    position = alloc_capital / entry_price_gross if entry_price_gross > 0 else 0
                    current_capital -= alloc_capital
                    entry_date = date
                    
            elif position > 0 and yesterday_signal == 0:
                exit_price = opens[i]
                exit_price_net = exit_price * (1 - cost_per_side)
                gross_pnl = (exit_price - entry_price) * position
                net_pnl = (exit_price_net - (entry_price * (1 + cost_per_side))) * position
                denom = (position * entry_price * (1+cost_per_side))
                ret_pct = net_pnl / denom if denom > 0 else 0
                current_capital += position * exit_price_net
                
                last_20_trades_pnl.append(ret_pct)
                if len(last_20_trades_pnl) > 20: last_20_trades_pnl.pop(0)
                
                trades_log.append({
                    "trade_id": trade_id_counter,
                    "entry_date": entry_date.strftime('%Y-%m-%d'),
                    "exit_date": date.strftime('%Y-%m-%d'),
                    "entry_price": float(entry_price),
                    "exit_price": float(exit_price),
                    "position_size": float(position),
                    "position_value": float(position * entry_price),
                    "gross_pnl": float(gross_pnl),
                    "net_pnl": float(net_pnl),
                    "return_pct": float(ret_pct),
                    "holding_period_days": (date - entry_date).days,
                    "exit_reason": "signal"
                })
                trade_id_counter += 1
                position = 0

        if position > 0:
            exit_reason = None
            exit_price = None
            
            if stop_loss_pct is not None:
                sl_price = entry_price * (1 - stop_loss_pct)
                if lows[i] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "stop_loss"
            
            if exit_reason is None and take_profit_pct is not None:
                tp_price = entry_price * (1 + take_profit_pct)
                if highs[i] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "take_profit"
                    
            if exit_reason is not None:
                exit_price_net = exit_price * (1 - cost_per_side)
                gross_pnl = (exit_price - entry_price) * position
                net_pnl = (exit_price_net - (entry_price * (1 + cost_per_side))) * position
                denom = (position * entry_price * (1+cost_per_side))
                ret_pct = net_pnl / denom if denom > 0 else 0
                current_capital += position * exit_price_net
                
                last_20_trades_pnl.append(ret_pct)
                if len(last_20_trades_pnl) > 20: last_20_trades_pnl.pop(0)
                
                trades_log.append({
                    "trade_id": trade_id_counter,
                    "entry_date": entry_date.strftime('%Y-%m-%d'),
                    "exit_date": date.strftime('%Y-%m-%d'),
                    "entry_price": float(entry_price),
                    "exit_price": float(exit_price),
                    "position_size": float(position),
                    "position_value": float(position * entry_price),
                    "gross_pnl": float(gross_pnl),
                    "net_pnl": float(net_pnl),
                    "return_pct": float(ret_pct),
                    "holding_period_days": (date - entry_date).days,
                    "exit_reason": exit_reason
                })
                trade_id_counter += 1
                position = 0

        if i == len(df) - 1:
            if position > 0:
                exit_price = closes[i]
                exit_price_net = exit_price * (1 - cost_per_side)
                gross_pnl = (exit_price - entry_price) * position
                net_pnl = (exit_price_net - (entry_price * (1 + cost_per_side))) * position
                current_capital += position * exit_price_net
                trades_log.append({
                    "trade_id": trade_id_counter,
                    "entry_date": entry_date.strftime('%Y-%m-%d'),
                    "exit_date": date.strftime('%Y-%m-%d'),
                    "entry_price": float(entry_price),
                    "exit_price": float(exit_price),
                    "position_size": float(position),
                    "position_value": float(position * entry_price),
                    "gross_pnl": float(gross_pnl),
                    "net_pnl": float(net_pnl),
                    "return_pct": float(net_pnl / (position * entry_price * (1+cost_per_side)) if position * entry_price > 0 else 0),
                    "holding_period_days": (date - entry_date).days,
                    "exit_reason": "end_of_data",
                    "liquidity_warning": True
                })
                position = 0
            
            bench_val = bench_df['Close'].iloc[-1] if not bench_df.empty else 1.0
            if isinstance(bench_val, pd.Series):
                bench_val = bench_val.iloc[-1]
            equity_curve.append({"date": date, "equity": current_capital, "benchmark": bench_val})
            break
        
        daily_equity = current_capital + (position * closes[i] if position > 0 else 0)
        
        bench_val = 1.0
        if date in bench_df.index:
            bench_val = bench_df.loc[date, 'Close']
            if isinstance(bench_val, pd.Series):
                bench_val = bench_val.iloc[0]
                
        equity_curve.append({
            "date": date,
            "equity": daily_equity,
            "benchmark": bench_val
        })

    eq_df = pd.DataFrame(equity_curve)
    eq_df.set_index('date', inplace=True)
    
    strategy_metrics = calculate_metrics(eq_df['equity'], initial_capital)
    
    bench_start = eq_df['benchmark'].iloc[0]
    if bench_start > 0:
        bnh_equity = initial_capital * (eq_df['benchmark'] / bench_start)
    else:
        bnh_equity = pd.Series(initial_capital, index=eq_df.index)
    bnh_metrics = calculate_metrics(bnh_equity, initial_capital)
    bnh_metrics.update({
        "total_trades": 0,
        "win_rate": 0.0,
        "avg_win": 0.0,
        "avg_loss": 0.0,
        "profit_factor": 0.0,
        "avg_holding_period": 0.0,
        "max_consecutive_wins": 0,
        "max_consecutive_losses": 0,
        "total_costs_paid": 0.0
    })
    
    strat_ret_series = eq_df['equity'].pct_change().dropna()
    bench_ret_series = bnh_equity.pct_change().dropna()
    
    common_idx = strat_ret_series.index.intersection(bench_ret_series.index)
    strat_ret_align = strat_ret_series.loc[common_idx]
    bench_ret_align = bench_ret_series.loc[common_idx]
    
    if len(strat_ret_align) > 1 and bench_ret_align.std() > 0:
        cov_matrix = np.cov(strat_ret_align, bench_ret_align)
        cov = cov_matrix[0, 1]
        var = np.var(bench_ret_align)
        beta = cov / var if var > 0 else 0
        
        annual_strat_ret = strategy_metrics['cagr']
        annual_bench_ret = bnh_metrics['cagr']
        alpha = annual_strat_ret - (beta * annual_bench_ret)
        
        tracking_error = (strat_ret_align - bench_ret_align).std() * np.sqrt(252)
        info_ratio = (annual_strat_ret - annual_bench_ret) / tracking_error if tracking_error > 0 else 0
    else:
        alpha = 0
        info_ratio = 0
        beta = 0
        
    strategy_metrics['alpha'] = float(alpha)
    strategy_metrics['information_ratio'] = float(info_ratio)
    strategy_metrics['beta'] = float(beta)

    winning_trades = [t for t in trades_log if t['net_pnl'] > 0]
    losing_trades = [t for t in trades_log if t['net_pnl'] <= 0]
    
    win_rate = len(winning_trades) / len(trades_log) if trades_log else 0
    avg_win = np.mean([t['net_pnl'] for t in winning_trades]) if winning_trades else 0
    avg_loss = np.mean([t['net_pnl'] for t in losing_trades]) if losing_trades else 0
    
    gross_profit = sum([t['gross_pnl'] for t in winning_trades])
    gross_loss = sum([t['gross_pnl'] for t in losing_trades])
    profit_factor = gross_profit / abs(gross_loss) if gross_loss != 0 else (float('inf') if gross_profit > 0 else 0)
    
    avg_holding_period = np.mean([t['holding_period_days'] for t in trades_log]) if trades_log else 0
    
    max_cons_wins = 0
    max_cons_losses = 0
    curr_wins = 0
    curr_losses = 0
    for t in trades_log:
        if t['net_pnl'] > 0:
            curr_wins += 1
            curr_losses = 0
            max_cons_wins = max(max_cons_wins, curr_wins)
        else:
            curr_losses += 1
            curr_wins = 0
            max_cons_losses = max(max_cons_losses, curr_losses)

    total_costs_paid = sum([abs(t['gross_pnl'] - t['net_pnl']) for t in trades_log])

    strategy_metrics.update({
        "total_trades": int(len(trades_log)),
        "win_rate": float(win_rate),
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "profit_factor": float(profit_factor),
        "avg_holding_period": float(avg_holding_period),
        "max_consecutive_wins": int(max_cons_wins),
        "max_consecutive_losses": int(max_cons_losses),
        "total_costs_paid": float(total_costs_paid)
    })
    
    drawdown_series = calculate_drawdown(eq_df['equity'])
    
    chart_data = []
    for date, row in eq_df.iterrows():
        chart_data.append({
            "time": date.strftime('%Y-%m-%d'),
            "equity": float(row['equity']),
            "bnh_equity": float(bnh_equity.loc[date]),
            "drawdown": float(drawdown_series.loc[date])
        })
        
    try:
        monthly_equity = eq_df['equity'].resample('ME').last()
    except ValueError:
        monthly_equity = eq_df['equity'].resample('M').last()
        
    monthly_returns_series = monthly_equity.pct_change().dropna()
    
    heatmap_data = []
    for date, ret in monthly_returns_series.items():
        heatmap_data.append({
            "year": int(date.year),
            "month": int(date.month),
            "return": float(ret)
        })

    res = {
        "metrics": {
            "strategy": strategy_metrics,
            "benchmark": bnh_metrics
        },
        "chart_data": chart_data,
        "trades": list(reversed(trades_log)),
        "heatmap": heatmap_data
    }
    
    return clean_nans(res)
