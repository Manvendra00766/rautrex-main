import pandas as pd
import numpy as np
from typing import Dict, Any, List

class BacktestingEngine:
    def __init__(self, initial_capital: float = 10000.0, fee_pct: float = 0.001, slippage_pct: float = 0.0005):
        self.initial_capital = initial_capital
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct

    def apply_slippage_and_fees(self, price: float, order_type: str) -> float:
        """Adjusts execution price for slippage and calculates fees."""
        # order_type is 'BUY' or 'SELL'
        if order_type == 'BUY':
            execution_price = price * (1 + self.slippage_pct)
            cost_with_fee = execution_price * (1 + self.fee_pct)
            return cost_with_fee
        elif order_type == 'SELL':
            execution_price = price * (1 - self.slippage_pct)
            proceeds_after_fee = execution_price * (1 - self.fee_pct)
            return proceeds_after_fee
        return price

    def run_sma_crossover(self, prices: pd.Series, short_window: int = 50, long_window: int = 200) -> Dict[str, Any]:
        """Runs an SMA crossover strategy backtest."""
        df = pd.DataFrame({'Close': prices})
        df['SMA_Short'] = df['Close'].rolling(window=short_window).mean()
        df['SMA_Long'] = df['Close'].rolling(window=long_window).mean()
        df.dropna(inplace=True)

        df['Signal'] = 0
        # 1 when short > long, else 0
        df.loc[df['SMA_Short'] > df['SMA_Long'], 'Signal'] = 1
        df['Position'] = df['Signal'].diff()

        return self._simulate_trades(df)

    def run_rsi_mean_reversion(self, prices: pd.Series, window: int = 14, lower_bound: int = 30, upper_bound: int = 70) -> Dict[str, Any]:
        """Runs an RSI mean reversion strategy backtest."""
        df = pd.DataFrame({'Close': prices})
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        df.dropna(inplace=True)

        df['Signal'] = 0
        df.loc[df['RSI'] < lower_bound, 'Signal'] = 1  # Buy
        df.loc[df['RSI'] > upper_bound, 'Signal'] = -1 # Sell (or flat)
        
        # Keep holding until opposite signal
        df['Signal'] = df['Signal'].replace(0, method='ffill')
        df['Signal'] = df['Signal'].clip(lower=0) # Long only for simplicity
        df['Position'] = df['Signal'].diff()

        return self._simulate_trades(df)

    def _simulate_trades(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Simulates trades given 'Close' and 'Position' (1 for buy, -1 for sell)."""
        cash = self.initial_capital
        shares = 0
        equity_curve = []
        trades = []

        for index, row in df.iterrows():
            price = row['Close']
            position_change = row.get('Position', 0)

            if position_change == 1 and cash > 0:
                # Buy
                cost_per_share = self.apply_slippage_and_fees(price, 'BUY')
                shares_bought = cash / cost_per_share
                shares += shares_bought
                cash = 0
                trades.append({'date': index, 'type': 'BUY', 'price': price, 'shares': shares_bought})
                
            elif position_change == -1 and shares > 0:
                # Sell
                proceeds_per_share = self.apply_slippage_and_fees(price, 'SELL')
                cash += shares * proceeds_per_share
                trades.append({'date': index, 'type': 'SELL', 'price': price, 'shares': shares})
                shares = 0
                
            nav = cash + (shares * price)
            equity_curve.append({'date': index, 'nav': nav})

        eq_df = pd.DataFrame(equity_curve).set_index('date')
        returns = eq_df['nav'].pct_change().dropna()
        
        total_return = (eq_df['nav'].iloc[-1] / self.initial_capital) - 1 if not eq_df.empty else 0
        annualized_return = (1 + total_return) ** (252 / len(eq_df)) - 1 if len(eq_df) > 0 else 0
        volatility = returns.std() * np.sqrt(252) if len(returns) > 0 else 0
        sharpe = (annualized_return - 0.02) / volatility if volatility > 0 else 0

        return {
            "equity_curve": equity_curve,
            "trades": trades,
            "metrics": {
                "total_return": total_return,
                "annualized_return": annualized_return,
                "volatility": volatility,
                "sharpe_ratio": sharpe,
                "total_trades": len(trades)
            }
        }
