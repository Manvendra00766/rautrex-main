import pytest
import json
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from services.signals_service import run_ml_pipeline_stream

@pytest.fixture
def mock_yf_download():
    with patch('yfinance.download') as mock:
        df = pd.DataFrame({
            'Open': [100.0] * 200,
            'High': [105.0] * 200,
            'Low': [95.0] * 200,
            'Close': [102.0] * 200,
            'Volume': [1000000] * 200
        }, index=pd.date_range(start='2023-01-01', periods=200))
        mock.return_value = df
        yield mock

@pytest.fixture(autouse=True)
def mock_common_dependencies():
    with patch('services.signals_service.create_notification') as mock_notify, \
         patch('os.path.exists', return_value=True), \
         patch('torch.load'), \
         patch('services.signals_service.train_lstm_generator') as mock_lstm_train, \
         patch('services.signals_service.train_trend_generator') as mock_trend_train, \
         patch('services.signals_service.train_garch_generator') as mock_garch_train, \
         patch('services.signals_service.train_anomaly_generator') as mock_anomaly_train:
        
        mock_lstm_train.return_value.__aiter__.return_value = []
        mock_trend_train.return_value.__aiter__.return_value = []
        mock_garch_train.return_value.__aiter__.return_value = []
        mock_anomaly_train.return_value.__aiter__.return_value = []
        
        yield {
            "notify": mock_notify
        }

@pytest.fixture
def mock_ml_models():
    with patch('joblib.load') as mock_joblib:
        # Mock Scalers
        mock_scaler_X = MagicMock()
        mock_scaler_X.transform.return_value = np.zeros((60, 12))
        
        mock_scaler_y = MagicMock()
        mock_scaler_y.inverse_transform.return_value = [[110.0]]
        
        # Mock Trend Model
        mock_trend = MagicMock()
        mock_trend.predict_proba.return_value = [[0.05, 0.05, 0.1, 0.4, 0.4]] # Strong Up
        mock_trend.feature_importances_ = [0.4, 0.3, 0.2, 0.1]
        
        # Mock GARCH
        mock_garch = MagicMock()
        mock_garch.forecast.return_value.variance.values = np.array([[2.5] * 30] * 200) # Vol ~ 1.58
        
        # Mock Anomaly
        mock_anomaly = MagicMock()
        mock_anomaly.predict.return_value = [1]
        
        mock_joblib.side_effect = [mock_scaler_X, mock_scaler_y, mock_trend, mock_garch, mock_anomaly]
        
        with patch('services.signals_service.LSTMModel') as mock_lstm_class:
            mock_lstm = mock_lstm_class.return_value
            mock_lstm.return_value = MagicMock(numpy=lambda: np.array([[0.8]]))
            yield {
                "trend": mock_trend,
                "garch": mock_garch,
                "sentiment": 0.5 # Positive
            }

@pytest.mark.asyncio
async def test_signal_breakdown_full_flow(mock_yf_download, mock_ml_models):
    with patch('services.signals_service.get_sentiment', return_value=(0.5, [{"title": "Good News", "sentiment": 0.5}])):
        gen = run_ml_pipeline_stream("AAPL", "550e8400-e29b-41d4-a716-446655440000")
        res = None
        async for msg in gen:
            if msg.startswith("data: "):
                data = json.loads(msg[6:])
                if "result" in data:
                    res = data["result"]
        
        assert res is not None
        
        # PART A — SIGNAL EXPLAINABILITY
        assert "lstm" in res["signal_breakdown"]
        assert "xgboost" in res["signal_breakdown"]
        assert "sentiment" in res["signal_breakdown"]
        
        # test_weights_sum_to_1
        weights = [
            res["signal_breakdown"]["lstm"]["weight"],
            res["signal_breakdown"]["xgboost"]["weight"],
            res["signal_breakdown"]["sentiment"]["weight"]
        ]
        assert sum(weights) == pytest.approx(1.0, abs=0.001)
        
        # test_contribution_formula
        for model in ["lstm", "xgboost", "sentiment"]:
            m = res["signal_breakdown"][model]
            assert m["contribution"] == pytest.approx(m["weight"] * m["confidence"], abs=0.1)
            
        # test_final_confidence_is_weighted_avg
        expected_weighted_conf = sum(res["signal_breakdown"][m]["contribution"] for m in ["lstm", "xgboost", "sentiment"])
        assert res["confidence"] == pytest.approx(expected_weighted_conf, abs=1.0)
        
        # test_top_features_count
        assert len(res["signal_breakdown"]["xgboost"]["top_features"]) == 3
        
        # test_feature_importance_positive
        for feat in res["signal_breakdown"]["xgboost"]["top_features"]:
            assert feat["importance"] > 0
            
        # test_feature_importance_sums_less_than_1
        total_imp = sum(f["importance"] for f in res["signal_breakdown"]["xgboost"]["top_features"])
        assert total_imp <= 1.0
        
        # test_reasoning_is_string
        assert isinstance(res["signal_breakdown"]["lstm"]["reasoning"], str)
        assert len(res["signal_breakdown"]["lstm"]["reasoning"]) > 0
        
        # test_risk_assessment_present
        risk = res["risk_assessment"]
        assert "volatility_regime" in risk
        assert "suggested_position_size_pct" in risk
        assert "risk_reward_ratio" in risk
        
        assert res["signal_validity_hours"] > 0
        assert "disclaimer" in res

@pytest.mark.asyncio
async def test_conflict_resolution_logic():
    async def get_final_result(lstm_ret, trend_probs, sent_score):
        with patch('yfinance.download', return_value=pd.DataFrame({'Close': [100]*200, 'Open':[100]*200, 'High':[100]*200, 'Low':[100]*200, 'Volume':[1000]*200}, index=pd.date_range('2023-01-01', periods=200))), \
             patch('joblib.load') as mock_joblib, \
             patch('services.signals_service.get_sentiment', return_value=(sent_score, [])), \
             patch('services.signals_service.LSTMModel') as mock_lstm_class:
            
            mock_scaler_X = MagicMock()
            mock_scaler_X.transform.return_value = np.zeros((60, 12))
            mock_scaler_y = MagicMock()
            mock_scaler_y.inverse_transform.return_value = [[100 * (1 + lstm_ret)]]
            
            mock_trend = MagicMock()
            mock_trend.predict_proba.return_value = [trend_probs]
            mock_trend.feature_importances_ = [0.25]*4
            
            mock_garch = MagicMock()
            mock_garch.forecast.return_value.variance.values = np.array([[1.0]*30]*200)
            
            mock_anomaly = MagicMock()
            mock_anomaly.predict.return_value = [1]
            
            mock_joblib.side_effect = [mock_scaler_X, mock_scaler_y, mock_trend, mock_garch, mock_anomaly]
            mock_lstm_class.return_value.return_value = MagicMock(numpy=lambda: np.array([[0.5]]))
            
            gen = run_ml_pipeline_stream("TEST", "550e8400-e29b-41d4-a716-446655440000")
            async for msg in gen:
                if "result" in msg:
                    return json.loads(msg[6:])["result"]

    # test_all_agree_high_confidence
    res = await get_final_result(0.05, [0, 0, 0, 0, 1], 0.8)
    assert res["final_signal"] == "BUY"
    assert res["confidence"] > 70
    
    # test_2_of_3_agree
    res = await get_final_result(0.05, [0, 0, 0, 0, 1], -0.8)
    assert res["final_signal"] == "BUY"
    
    # test_all_disagree_hold
    res = await get_final_result(0.05, [1, 0, 0, 0, 0], 0)
    assert res["final_signal"] == "HOLD"
    
    assert 0 <= res["confidence"] <= 100
    assert res["final_signal"] in ["BUY", "SELL", "HOLD"]

@pytest.mark.asyncio
async def test_lstm_specific_logic(mock_yf_download):
     with patch('joblib.load') as mock_joblib, \
          patch('services.signals_service.get_sentiment', return_value=(0, [])), \
          patch('services.signals_service.LSTMModel') as mock_lstm_class:
            
            mock_scaler_X = MagicMock()
            mock_scaler_X.transform.return_value = np.zeros((60, 12))
            mock_scaler_y = MagicMock()
            mock_scaler_y.inverse_transform.return_value = [[110.0]]
            
            mock_trend = MagicMock()
            mock_trend.predict_proba.return_value = [[0,0,1,0,0]]
            mock_trend.feature_importances_ = [0.25]*4
            mock_garch = MagicMock()
            mock_garch.forecast.return_value.variance.values = np.array([[1.0]*30]*200)
            mock_anomaly = MagicMock()
            mock_anomaly.predict.return_value = [1]
            
            mock_joblib.side_effect = [mock_scaler_X, mock_scaler_y, mock_trend, mock_garch, mock_anomaly]
            mock_lstm_class.return_value.return_value = MagicMock(numpy=lambda: np.array([[0.5]]))
            
            gen = run_ml_pipeline_stream("TEST", "550e8400-e29b-41d4-a716-446655440000")
            res = {}
            async for msg in gen:
                if "result" in msg:
                    res = json.loads(msg[6:])["result"]
                    break

            lstm = res["signal_breakdown"]["lstm"]
            assert lstm["predicted_price"] > 0
            expected_ret = (lstm["predicted_price"] - lstm["current_price"]) / lstm["current_price"] * 100
            assert lstm["expected_return_pct"] == pytest.approx(expected_ret, abs=0.01)

@pytest.mark.asyncio
async def test_xgboost_feature_values(mock_yf_download, mock_ml_models):
    with patch('services.signals_service.get_sentiment', return_value=(0, [])):
        gen = run_ml_pipeline_stream("AAPL", "550e8400-e29b-41d4-a716-446655440000")
        res = {}
        async for msg in gen:
            if "result" in msg:
                res = json.loads(msg[6:])["result"]
                break
        
        xgb_feats = res["signal_breakdown"]["xgboost"]["top_features"]
        rsi_feat = next(f for f in xgb_feats if "RSI" in f["feature"])
        assert 0 <= rsi_feat["value"] <= 100
        atr_feat = next(f for f in xgb_feats if "ATR" in f["feature"])
        assert atr_feat["value"] > 0
