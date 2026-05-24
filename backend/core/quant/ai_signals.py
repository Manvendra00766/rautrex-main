import numpy as np
import pandas as pd
from typing import Dict, Any, List
import joblib

try:
    import xgboost as xgb
    from sklearn.ensemble import RandomForestClassifier
except ImportError:
    xgb = None
    RandomForestClassifier = None

class AISignalsEngine:
    def __init__(self):
        self.models = {}

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Generate technical indicators as features for ML models."""
        features = df.copy()
        features['Returns'] = features['Close'].pct_change()
        
        # SMA
        features['SMA_10'] = features['Close'].rolling(window=10).mean()
        features['SMA_50'] = features['Close'].rolling(window=50).mean()
        features['SMA_Ratio'] = features['SMA_10'] / features['SMA_50']
        
        # Volatility
        features['Vol_20'] = features['Returns'].rolling(window=20).std() * np.sqrt(252)
        
        # Momentum
        features['Momentum_10'] = features['Close'] / features['Close'].shift(10) - 1
        
        features.dropna(inplace=True)
        return features

    def train_random_forest(self, symbol: str, df: pd.DataFrame):
        """Train a simple Random Forest model to predict next day direction."""
        if not RandomForestClassifier:
            raise ImportError("scikit-learn is not installed.")
            
        features = self.generate_features(df)
        
        # Target: 1 if next day return > 0 else 0
        features['Target'] = (features['Returns'].shift(-1) > 0).astype(int)
        features.dropna(inplace=True)
        
        X = features.drop(['Target', 'Close'], axis=1, errors='ignore')
        y = features['Target']
        
        model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
        model.fit(X, y)
        self.models[f"{symbol}_rf"] = model
        
        return model

    def train_xgboost(self, symbol: str, df: pd.DataFrame):
        """Train an XGBoost model."""
        if not xgb:
            raise ImportError("xgboost is not installed.")
            
        features = self.generate_features(df)
        features['Target'] = (features['Returns'].shift(-1) > 0).astype(int)
        features.dropna(inplace=True)
        
        X = features.drop(['Target', 'Close'], axis=1, errors='ignore')
        y = features['Target']
        
        model = xgb.XGBClassifier(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
        model.fit(X, y)
        self.models[f"{symbol}_xgb"] = model
        
        return model

    def predict_signal(self, symbol: str, df: pd.DataFrame, model_type: str = "rf") -> Dict[str, Any]:
        """Predict the signal (BUY, SELL, HOLD) using a trained model."""
        model_key = f"{symbol}_{model_type}"
        if model_key not in self.models:
            # Fallback to random forest training if missing
            self.train_random_forest(symbol, df)
            model_key = f"{symbol}_rf"

        model = self.models[model_key]
        features = self.generate_features(df)
        
        if features.empty:
            return {"signal": "HOLD", "confidence": 0.0, "reason": "Not enough data for features."}
            
        # Get the latest row of features
        latest_features = features.drop(['Close', 'Target'], axis=1, errors='ignore').iloc[-1:]
        
        # Predict probability
        prob = model.predict_proba(latest_features)[0]
        prob_up = prob[1]
        
        # Interpret
        if prob_up > 0.60:
            signal = "BUY"
            confidence = prob_up
            reason = "Model indicates strong upward momentum based on short-term SMA and low volatility."
        elif prob_up < 0.40:
            signal = "SELL"
            confidence = 1 - prob_up
            reason = "Model indicates downward trend likely due to weakening momentum."
        else:
            signal = "HOLD"
            confidence = max(prob_up, 1 - prob_up)
            reason = "Market signals are mixed; volatility and moving averages do not present a clear edge."

        return {
            "signal": signal,
            "confidence": float(confidence),
            "reason": reason
        }

    def save_model(self, symbol: str, model_type: str, path: str):
        model_key = f"{symbol}_{model_type}"
        if model_key in self.models:
            joblib.dump(self.models[model_key], path)

    def load_model(self, symbol: str, model_type: str, path: str):
        model_key = f"{symbol}_{model_type}"
        self.models[model_key] = joblib.load(path)
