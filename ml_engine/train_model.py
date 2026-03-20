"""
ml_engine/train_model.py
------------------------
Trains RandomForest, XGBoost, and LSTM models on historical data.
Adapts to available data size — works with as few as 5 rows for RF/XGB,
and 10+ rows for LSTM.
"""

from __future__ import annotations

import os
from typing import Any

import joblib
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
import xgboost as xgb

from config import settings
from data_pipeline.feature_engineering import FEATURE_COLUMNS, feature_engineering
from data_pipeline.preprocess import clean_market_data
from ml_engine.evaluate_model import evaluate_regression
from ml_engine.save_model import save_sklearn_model, save_lstm_model

MIN_ROWS_SKLEARN = 5    # Minimum rows needed for RF / XGBoost
MIN_ROWS_LSTM    = 10   # Minimum rows needed for LSTM


def _load_features(coin: str) -> tuple[pd.DataFrame, pd.Series]:
    raw = clean_market_data(coin, lookback_days=365)
    if raw.empty:
        raise ValueError(f"No data available for {coin}")
    df = feature_engineering(raw)
    if len(df) < MIN_ROWS_SKLEARN:
        raise ValueError(
            f"Only {len(df)} usable rows for {coin} — need at least "
            f"{MIN_ROWS_SKLEARN}. Keep the pipeline running to collect more data."
        )
    available = [c for c in FEATURE_COLUMNS if c in df.columns]
    return df[available], df["target_price_next"]


def train_random_forest(coin: str) -> dict[str, Any]:
    logger.info(f"[{coin}] Training RandomForest ...")
    X, y = _load_features(coin)

    # With very little data use a single holdout row instead of 20%
    test_size = max(1, int(len(X) * 0.2))
    X_train, X_test = X.iloc[:-test_size], X.iloc[-test_size:]
    y_train, y_test = y.iloc[:-test_size], y.iloc[-test_size:]

    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    metrics = evaluate_regression(model, X_test, y_test)
    save_sklearn_model(model, coin, "random_forest")
    logger.success(f"[{coin}] RF — RMSE={metrics['rmse']:.2f}  R²={metrics['r2']:.4f}")
    return {"model_name": "random_forest", **metrics}


def train_xgboost(coin: str) -> dict[str, Any]:
    logger.info(f"[{coin}] Training XGBoost ...")
    X, y = _load_features(coin)

    test_size = max(1, int(len(X) * 0.2))
    X_train, X_test = X.iloc[:-test_size], X.iloc[-test_size:]
    y_train, y_test = y.iloc[:-test_size], y.iloc[-test_size:]

    model = xgb.XGBRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=4,
        random_state=42,
        verbosity=0,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    metrics = evaluate_regression(model, X_test, y_test)
    save_sklearn_model(model, coin, "xgboost")
    logger.success(f"[{coin}] XGB — RMSE={metrics['rmse']:.2f}  R²={metrics['r2']:.4f}")
    return {"model_name": "xgboost", **metrics}


def _build_lstm_sequences(series, look_back):
    X, y = [], []
    for i in range(len(series) - look_back):
        X.append(series[i: i + look_back])
        y.append(series[i + look_back])
    return np.array(X), np.array(y)


def train_lstm(coin: str) -> dict[str, Any]:
    import tensorflow as tf
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.callbacks import EarlyStopping

    logger.info(f"[{coin}] Training LSTM ...")
    raw = clean_market_data(coin, lookback_days=365)
    if raw.empty or len(raw) < MIN_ROWS_LSTM:
        raise ValueError(
            f"Need at least {MIN_ROWS_LSTM} rows for LSTM, have {len(raw)}. "
            "Keep pipeline running to collect more data."
        )

    prices = raw["price"].values.reshape(-1, 1)
    scaler = MinMaxScaler()
    prices_scaled = scaler.fit_transform(prices).flatten()

    # Adapt look_back to available data (max 30, min 2)
    look_back = min(30, max(2, len(prices_scaled) // 3))
    logger.info(f"[{coin}] LSTM look_back={look_back} (data rows={len(prices_scaled)})")

    X, y = _build_lstm_sequences(prices_scaled, look_back)
    if len(X) < 4:
        raise ValueError(f"Not enough sequences ({len(X)}) to train LSTM. Need more data.")

    X = X.reshape(X.shape[0], X.shape[1], 1)
    split = max(1, int(len(X) * 0.8))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    model = Sequential([
        LSTM(32, return_sequences=False, input_shape=(look_back, 1)),
        Dropout(0.1),
        Dense(16, activation="relu"),
        Dense(1),
    ])
    model.compile(optimizer="adam", loss="mse")
    early_stop = EarlyStopping(patience=5, restore_best_weights=True)

    model.fit(
        X_train, y_train,
        epochs=50,
        batch_size=max(1, min(8, len(X_train))),
        validation_split=0.1 if len(X_train) > 5 else 0.0,
        callbacks=[early_stop],
        verbose=0,
    )

    y_pred_scaled = model.predict(X_test, verbose=0).flatten()
    y_pred   = scaler.inverse_transform(y_pred_scaled.reshape(-1, 1)).flatten()
    y_actual = scaler.inverse_transform(y_test.reshape(-1, 1)).flatten()
    rmse = float(np.sqrt(np.mean((y_pred - y_actual) ** 2)))

    # Save look_back alongside the model so predictor knows what to use
    save_lstm_model(model, scaler, coin)
    joblib.dump(look_back, os.path.join(settings.models_dir, coin, "lstm_look_back.joblib"))

    logger.success(f"[{coin}] LSTM — RMSE={rmse:.2f}")
    return {"model_name": "lstm", "rmse": rmse}


def train_all_models(coin: str) -> list[dict[str, Any]]:
    """Train RF, XGBoost, and LSTM for the given coin."""
    results = []
    for trainer in [train_random_forest, train_xgboost, train_lstm]:
        try:
            results.append(trainer(coin))
        except Exception as exc:
            logger.error(f"[{coin}] {trainer.__name__} failed: {exc}")
    return results


if __name__ == "__main__":
    import sys
    coin = sys.argv[1] if len(sys.argv) > 1 else "bitcoin"
    results = train_all_models(coin)
    for r in results:
        print(r)