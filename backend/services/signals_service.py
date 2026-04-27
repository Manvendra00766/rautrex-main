import os
import json
import asyncio
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import joblib

# ML Libraries
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import MinMaxScaler
from sklearn.ensemble import IsolationForest, RandomForestClassifier
import xgboost as xgb
from arch import arch_model
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import ta
from utils import clean_nans

CACHE_DIR = "models_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# --- 1. PRICE PREDICTION: PyTorch LSTM ---
class LSTMModel(nn.Module):
    def __init__(self, input_dim, hidden_dim=64, num_layers=2, output_dim=1):
        super(LSTMModel, self).__init__()
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_dim).to(x.device)
        out, (hn, cn) = self.lstm(x, (h0, c0))
        out = self.fc(out[:, -1, :]) 
        return out

def add_technical_indicators(df):
    df = df.copy()
    try:
        # Handle cases where indicators might fail due to small data
        df['rsi'] = ta.momentum.RSIIndicator(df['Close'], window=14).rsi()
        macd = ta.trend.MACD(df['Close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        bb = ta.volatility.BollingerBands(df['Close'])
        df['bb_high'] = bb.bollinger_hband()
        df['bb_low'] = bb.bollinger_lband()
        df['atr'] = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close']).average_true_range()
        df['obv'] = ta.volume.OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()
        return df.dropna()
    except Exception as e:
        print(f"Indicator calculation error: {e}")
        return df

async def train_lstm_generator(ticker: str, df: pd.DataFrame):
    yield {"status": "Processing data for LSTM...", "progress": 10}
    await asyncio.sleep(0.01)
    
    try:
        features = ['Open', 'High', 'Low', 'Close', 'Volume', 'rsi', 'macd', 'macd_signal', 'bb_high', 'bb_low', 'atr', 'obv']
        data = df[features].values
        target = df['Close'].values.reshape(-1, 1)
        
        scaler_X = MinMaxScaler()
        scaler_y = MinMaxScaler()
        
        data_scaled = scaler_X.fit_transform(data)
        target_scaled = scaler_y.fit_transform(target)
        
        seq_length = 60
        if len(data_scaled) <= seq_length:
            raise ValueError(f"Insufficient data for LSTM. Need > {seq_length} points.")

        X, y = [], []
        for i in range(len(data_scaled) - seq_length):
            X.append(data_scaled[i:(i + seq_length)])
            y.append(target_scaled[i])
            
        X = torch.tensor(np.array(X), dtype=torch.float32)
        y = torch.tensor(np.array(y), dtype=torch.float32)
        
        dataset = TensorDataset(X, y)
        loader = DataLoader(dataset, batch_size=32, shuffle=True)
        
        model = LSTMModel(input_dim=len(features))
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
        
        epochs = 5 
        for epoch in range(epochs):
            model.train()
            for batch_X, batch_y in loader:
                optimizer.zero_grad()
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
            
            progress = 10 + int((epoch + 1) / epochs * 30)
            yield {"status": f"Training LSTM Epoch {epoch+1}/{epochs}", "progress": progress}
            await asyncio.sleep(0.01)
            
        torch.save(model.state_dict(), f"{CACHE_DIR}/{ticker}_lstm.pth")
        joblib.dump(scaler_X, f"{CACHE_DIR}/{ticker}_scaler_X.pkl")
        joblib.dump(scaler_y, f"{CACHE_DIR}/{ticker}_scaler_y.pkl")
        
        yield {"status": "LSTM Training Complete.", "progress": 40}
    except Exception as e:
        yield {"status": f"LSTM Error: {str(e)}", "progress": 40, "error": True}

async def train_trend_generator(ticker: str, df: pd.DataFrame):
    yield {"status": "Training Trend Classifier (XGBoost)...", "progress": 50}
    await asyncio.sleep(0.01)
    
    try:
        features = ['rsi', 'macd', 'atr', 'obv']
        X = df[features].values
        future_returns = df['Close'].pct_change(5).shift(-5)
        
        # Use 3-bin classification (Down, Neutral, Up) for more robustness with less data
        y_raw = pd.qcut(future_returns, 3, labels=[0, 1, 2], duplicates='drop')
        y = y_raw.dropna()
        
        if len(y) < 20:
            raise ValueError("Insufficient data for Trend Classification")

        X_train = X[:len(y)]
        model = xgb.XGBClassifier(n_estimators=50, max_depth=3, learning_rate=0.1)
        model.fit(X_train, y)
        
        joblib.dump(model, f"{CACHE_DIR}/{ticker}_trend.pkl")
        yield {"status": "Trend Classifier Trained.", "progress": 60}
    except Exception as e:
        yield {"status": f"Trend Error: {str(e)}", "progress": 60, "error": True}

async def train_garch_generator(ticker: str, df: pd.DataFrame):
    yield {"status": "Fitting GARCH(1,1) Volatility Model...", "progress": 70}
    await asyncio.sleep(0.01)
    
    try:
        returns = 100 * df['Close'].pct_change().dropna()
        if len(returns) < 100:
            raise ValueError("Insufficient data for GARCH")

        am = arch_model(returns, vol='Garch', p=1, q=1, rescale=False)
        res = am.fit(disp='off')
        joblib.dump(res, f"{CACHE_DIR}/{ticker}_garch.pkl")
        yield {"status": "GARCH Model Fitted.", "progress": 80}
    except Exception as e:
        yield {"status": f"GARCH Error: {str(e)}", "progress": 80, "error": True}

def get_sentiment(ticker: str):
    try:
        tk = yf.Ticker(ticker)
        news = tk.news
        analyzer = SentimentIntensityAnalyzer()
        
        if not news:
            return 0.1, [] # default neutral-positive
            
        scores = []
        headlines = []
        for item in news[:5]:
            title = item.get('title', '')
            score = analyzer.polarity_scores(title)['compound']
            scores.append(score)
            headlines.append({"title": title, "sentiment": score})
            
        avg_score = np.mean(scores) if scores else 0
        return avg_score, headlines
    except:
        return 0, []

async def train_anomaly_generator(ticker: str, df: pd.DataFrame):
    yield {"status": "Detecting Anomalies (Isolation Forest)...", "progress": 90}
    await asyncio.sleep(0.01)
    
    try:
        features = ['Close', 'Volume', 'atr']
        X = df[features].values
        iso = IsolationForest(contamination=0.01, random_state=42)
        iso.fit(X)
        joblib.dump(iso, f"{CACHE_DIR}/{ticker}_anomaly.pkl")
        yield {"status": "Anomaly Detection Complete.", "progress": 95}
    except Exception as e:
        yield {"status": f"Anomaly Error: {str(e)}", "progress": 95, "error": True}

from services.notification_service import create_notification

_TRAINING_LOCKS = {}
_TRAINING_RESULTS = {}

def get_ticker_lock(ticker: str):
    if ticker not in _TRAINING_LOCKS:
        _TRAINING_LOCKS[ticker] = asyncio.Lock()
    return _TRAINING_LOCKS[ticker]

async def run_ml_pipeline_stream(ticker: str, user_id: str):
    ticker = ticker.upper()
    lock = get_ticker_lock(ticker)
    
    async with lock:
        if ticker in _TRAINING_RESULTS:
            last_res, timestamp = _TRAINING_RESULTS[ticker]
            if datetime.now() - timestamp < timedelta(minutes=30):
                yield f"data: {json.dumps(clean_nans(last_res))}\n\n"
                return

        try:
            df_raw = yf.download(ticker, period="2y", progress=False)
            if df_raw.empty:
                yield f"data: {json.dumps({'error': f'No data for {ticker}'})}\n\n"
                return
                
            if isinstance(df_raw.columns, pd.MultiIndex):
                df = df_raw.copy()
                df.columns = df.columns.get_level_values(0)
            else:
                df = df_raw.copy()

            df = add_technical_indicators(df)
            if len(df) < 80:
                 yield f"data: {json.dumps({'error': 'Insufficient history.'})}\n\n"
                 return

            async for msg in train_lstm_generator(ticker, df): yield f"data: {json.dumps(msg)}\n\n"
            async for msg in train_trend_generator(ticker, df): yield f"data: {json.dumps(msg)}\n\n"
            async for msg in train_garch_generator(ticker, df): yield f"data: {json.dumps(msg)}\n\n"
            async for msg in train_anomaly_generator(ticker, df): yield f"data: {json.dumps(msg)}\n\n"
            
            # --- Inference ---
            current_price = float(df['Close'].iloc[-1])
            pred_price = current_price
            
            if os.path.exists(f"{CACHE_DIR}/{ticker}_lstm.pth"):
                model_lstm = LSTMModel(12)
                model_lstm.load_state_dict(torch.load(f"{CACHE_DIR}/{ticker}_lstm.pth"))
                model_lstm.eval()
                scaler_X = joblib.load(f"{CACHE_DIR}/{ticker}_scaler_X.pkl")
                scaler_y = joblib.load(f"{CACHE_DIR}/{ticker}_scaler_y.pkl")
                recent = df[['Open', 'High', 'Low', 'Close', 'Volume', 'rsi', 'macd', 'macd_signal', 'bb_high', 'bb_low', 'atr', 'obv']].values[-60:]
                X_pred = torch.tensor(np.array([scaler_X.transform(recent)]), dtype=torch.float32)
                with torch.no_grad(): pred_scaled = model_lstm(X_pred).numpy()
                pred_price = float(scaler_y.inverse_transform(pred_scaled)[0][0])
            
            predicted_return = (pred_price - current_price) / current_price
            
            trend_class = "Neutral"
            trend_probs = [0, 1, 0]
            if os.path.exists(f"{CACHE_DIR}/{ticker}_trend.pkl"):
                model_trend = joblib.load(f"{CACHE_DIR}/{ticker}_trend.pkl")
                recent_feat = df[['rsi', 'macd', 'atr', 'obv']].values[-1:]
                trend_probs = model_trend.predict_proba(recent_feat)[0]
                classes = ["Down", "Neutral", "Up"]
                trend_class = classes[np.argmax(trend_probs)]
            
            vol_regime = "medium"
            if os.path.exists(f"{CACHE_DIR}/{ticker}_garch.pkl"):
                res_garch = joblib.load(f"{CACHE_DIR}/{ticker}_garch.pkl")
                vol_pred = np.sqrt(res_garch.forecast(horizon=1).variance.values[-1, :])[0]
                vol_regime = "high" if vol_pred > 2 else "low" if vol_pred < 1 else "medium"
            
            sent_score, headlines = get_sentiment(ticker)
            
            # Simple Ensemble
            score = 0
            if predicted_return > 0.02: score += 1
            elif predicted_return < -0.02: score -= 1
            if trend_class == "Up": score += 1
            elif trend_class == "Down": score -= 1
            if sent_score > 0.1: score += 1
            elif sent_score < -0.1: score -= 1
            
            final_signal = "BUY" if score >= 2 else "SELL" if score <= -2 else "HOLD"
            confidence = min(max(50 + abs(score) * 15, 50), 95)
            stop_loss_pct = 7.0 if vol_regime == "high" else 5.0 if vol_regime == "medium" else 3.0
            suggested_position_size_pct = max(2.5, min(15.0, confidence / 8 if vol_regime != "high" else confidence / 10))
            reward_target_pct = max(abs(predicted_return) * 100 * 1.5, stop_loss_pct * 1.2)
            risk_reward_ratio = reward_target_pct / stop_loss_pct if stop_loss_pct else 0
            
            final_res = {
                "status": "Complete", 
                "progress": 100, 
                "result": {
                    "ticker": ticker, 
                    "current_price": current_price,
                    "final_signal": final_signal,
                    "confidence": float(confidence),
                    "signal_breakdown": {
                        "lstm": {"predicted_price": pred_price, "expected_return": float(predicted_return)},
                        "xgboost": {"trend": trend_class, "confidence": float(max(trend_probs))},
                        "sentiment": {"score": float(sent_score), "count": len(headlines), "recent_headlines": headlines},
                        "model_scores": {
                            "lstm_expected_return_pct": float(predicted_return * 100),
                            "xgboost_confidence_pct": float(max(trend_probs) * 100),
                            "sentiment_score": float(sent_score),
                        },
                    },
                    "risk_assessment": {
                        "volatility": vol_regime,
                        "suggested_stop_loss_pct": float(stop_loss_pct),
                        "suggested_position_size_pct": float(suggested_position_size_pct),
                        "reward_target_pct": float(reward_target_pct),
                        "risk_reward_ratio": float(risk_reward_ratio),
                    }
                }
            }
            
            _TRAINING_RESULTS[ticker] = (final_res, datetime.now())
            await create_notification(user_id, "signal", f"ML Signal: {ticker}", f"{final_signal} ({int(confidence)}%)")
            yield f"data: {json.dumps(clean_nans(final_res))}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

async def scan_market():
    tickers = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN", "META", "TSLA", "NFLX", "AMD", "COIN"]
    results = []
    try:
        data = yf.download(tickers, period="1mo", progress=False)
        if 'Close' in data.columns:
            prices = data['Close']
        else:
            prices = data.xs('Close', axis=1, level=0)
            
        for tk in tickers:
            if tk not in prices.columns: continue
            tk_prices = prices[tk].dropna()
            if len(tk_prices) < 10: continue
            
            ret = (tk_prices.iloc[-1] - tk_prices.iloc[-5]) / tk_prices.iloc[-5]
            rsi = ta.momentum.RSIIndicator(tk_prices, window=10).rsi().iloc[-1]
            
            if ret > 0.03 and rsi < 70: signal = "BUY"
            elif ret < -0.03 and rsi > 30: signal = "SELL"
            else: signal = "HOLD"
            
            results.append({"ticker": tk, "price": float(tk_prices.iloc[-1]), "signal": signal, "confidence": 70.0, "change": float(ret)})
            
    except Exception as e:
        print(f"Scan error: {e}")
        
    return clean_nans({"scan_results": results})
