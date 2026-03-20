"""
prediction_service/predictor.py
--------------------------------
Loads trained models and generates next-price predictions with
confidence scores and trend labels.

Public API
----------
predict_price(coin, model_name) → PredictionResult
save_prediction(result)         → None
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from loguru import logger

from config import settings
from data_pipeline.feature_engineering import FEATURE_COLUMNS, feature_engineering
from data_pipeline.preprocess import clean_market_data
from database.db_connector import ModelPrediction, SessionLocal, TrendEnum
from ml_engine.save_model import load_lstm_model, load_sklearn_model


LSTM_LOOK_BACK = 30


# ── Result Schema ─────────────────────────────────────────────────────────────

@dataclass
class PredictionResult:
    coin: str
    model_name: str
    predicted_price: float
    current_price: float
    confidence: float          # 0–1
    trend: str                 # "bullish" | "bearish" | "neutral"
    prediction_time: datetime
    target_time: datetime      # when the prediction applies to

    def to_dict(self) -> dict:
        return {
            "coin": self.coin,
            "model_name": self.model_name,
            "predicted_price": round(self.predicted_price, 4),
            "current_price": round(self.current_price, 4),
            "confidence": round(self.confidence, 4),
            "trend": self.trend,
            "prediction_time": self.prediction_time.isoformat(),
            "target_time": self.target_time.isoformat(),
        }


# ── Internals ─────────────────────────────────────────────────────────────────

def _determine_trend(current: float, predicted: float, threshold: float = 0.005) -> str:
    """
    Label the trend based on predicted price change.

    Parameters
    ----------
    threshold : float
        Minimum percentage change to declare bullish/bearish (default 0.5 %).
    """
    change_pct = (predicted - current) / current
    if change_pct > threshold:
        return TrendEnum.bullish
    if change_pct < -threshold:
        return TrendEnum.bearish
    return TrendEnum.neutral


def _confidence_from_rf(model, X_last: pd.DataFrame) -> float:
    """
    Estimate confidence from RandomForest tree variance.

    A low inter-tree RMSE relative to predicted value → high confidence.
    """
    tree_preds = np.array([t.predict(X_last.values) for t in model.estimators_])
    pred_mean = tree_preds.mean()
    pred_std = tree_preds.std()
    # Coefficient of variation: lower = more confident
    cv = pred_std / (abs(pred_mean) + 1e-9)
    return float(np.clip(1 - cv, 0, 1))


def _predict_sklearn(coin: str, model_name: str) -> PredictionResult:
    model = load_sklearn_model(coin, model_name)
    raw = clean_market_data(coin, lookback_days=90)
    df = feature_engineering(raw)

    available = [c for c in FEATURE_COLUMNS if c in df.columns]
    X_last = df[available].iloc[[-1]]   # Most recent row
    current_price = float(raw["price"].iloc[-1])

    predicted_price = float(model.predict(X_last)[0])

    if model_name == "random_forest":
        confidence = _confidence_from_rf(model, X_last)
    else:
        # XGBoost — use a simple heuristic based on leaf count
        confidence = 0.70   # placeholder; can be improved with conformal prediction

    trend = _determine_trend(current_price, predicted_price)
    now = datetime.utcnow()

    return PredictionResult(
        coin=coin,
        model_name=model_name,
        predicted_price=predicted_price,
        current_price=current_price,
        confidence=confidence,
        trend=trend,
        prediction_time=now,
        target_time=now + timedelta(minutes=settings.data_refresh_interval_minutes),
    )


def _predict_lstm(coin: str) -> PredictionResult:
    model, scaler = load_lstm_model(coin)
    raw = clean_market_data(coin, lookback_days=90)
    prices = raw["price"].values
    current_price = float(prices[-1])

    # Build the last look-back window
    window = prices[-LSTM_LOOK_BACK:]
    if len(window) < LSTM_LOOK_BACK:
        raise ValueError(f"Not enough data for LSTM look-back ({len(window)} < {LSTM_LOOK_BACK})")

    window_scaled = scaler.transform(window.reshape(-1, 1))
    X = window_scaled.reshape(1, LSTM_LOOK_BACK, 1)

    pred_scaled = model.predict(X, verbose=0)
    predicted_price = float(scaler.inverse_transform(pred_scaled)[0][0])

    trend = _determine_trend(current_price, predicted_price)
    confidence = 0.65   # LSTM — requires separate calibration; placeholder

    now = datetime.utcnow()
    return PredictionResult(
        coin=coin,
        model_name="lstm",
        predicted_price=predicted_price,
        current_price=current_price,
        confidence=confidence,
        trend=trend,
        prediction_time=now,
        target_time=now + timedelta(minutes=settings.data_refresh_interval_minutes),
    )


# ── Public API ────────────────────────────────────────────────────────────────

def predict_price(
    coin: str,
    model_name: str = "xgboost",
) -> PredictionResult:
    """
    Generate a price prediction for the given coin.

    Parameters
    ----------
    coin : str
        CoinGecko slug, e.g. "bitcoin"
    model_name : str
        "random_forest" | "xgboost" | "lstm"

    Returns
    -------
    PredictionResult
    """
    logger.info(f"Predicting {coin} with {model_name} …")
    if model_name == "lstm":
        result = _predict_lstm(coin)
    else:
        result = _predict_sklearn(coin, model_name)

    logger.success(
        f"[{coin}/{model_name}] predicted=${result.predicted_price:.2f} "
        f"confidence={result.confidence:.2%} trend={result.trend}"
    )
    return result


def save_prediction(result: PredictionResult) -> None:
    """Persist a PredictionResult to the database."""
    db = SessionLocal()
    try:
        record = ModelPrediction(
            coin=result.coin,
            model_name=result.model_name,
            predicted_price=result.predicted_price,
            confidence=result.confidence,
            trend=TrendEnum(result.trend),
            prediction_time=result.prediction_time,
            target_time=result.target_time,
        )
        db.add(record)
        db.commit()
        logger.info(f"Prediction saved for {result.coin}.")
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to save prediction: {exc}")
    finally:
        db.close()


# ── CLI entry ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, json
    coin = sys.argv[1] if len(sys.argv) > 1 else "bitcoin"
    model = sys.argv[2] if len(sys.argv) > 2 else "xgboost"
    result = predict_price(coin, model)
    print(json.dumps(result.to_dict(), indent=2))
