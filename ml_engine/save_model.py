"""
ml_engine/save_model.py
-----------------------
Serialises trained models to disk.

Conventions
-----------
- sklearn/xgb  → models/<coin>/<model_name>.joblib
- LSTM          → models/<coin>/lstm_model/  (SavedModel format)
                  models/<coin>/lstm_scaler.joblib
"""

from __future__ import annotations

import os

import joblib
from loguru import logger

from config import settings


def _coin_dir(coin: str) -> str:
    path = os.path.join(settings.models_dir, coin)
    os.makedirs(path, exist_ok=True)
    return path


def save_sklearn_model(model, coin: str, model_name: str) -> str:
    """
    Persist a sklearn-compatible model with joblib.

    Parameters
    ----------
    model : estimator
        Fitted sklearn / xgboost model.
    coin : str
        e.g. "bitcoin"
    model_name : str
        e.g. "random_forest" | "xgboost"

    Returns
    -------
    str
        Absolute path to the saved file.
    """
    path = os.path.join(_coin_dir(coin), f"{model_name}.joblib")
    joblib.dump(model, path)
    logger.info(f"Model saved → {path}")
    return path


def save_lstm_model(model, scaler, coin: str) -> tuple[str, str]:
    """
    Save a Keras LSTM model (SavedModel format) and its MinMaxScaler.

    Parameters
    ----------
    model : keras.Model
        Trained LSTM model.
    scaler : MinMaxScaler
        Scaler fitted on training prices.
    coin : str

    Returns
    -------
    tuple[str, str]
        (model_path, scaler_path)
    """
    d = _coin_dir(coin)
    model_path = os.path.join(d, "lstm_model")
    scaler_path = os.path.join(d, "lstm_scaler.joblib")

    model.save(model_path)
    joblib.dump(scaler, scaler_path)

    logger.info(f"LSTM model saved → {model_path}")
    logger.info(f"LSTM scaler saved → {scaler_path}")
    return model_path, scaler_path


def load_sklearn_model(coin: str, model_name: str):
    """Load a previously saved sklearn/xgb model."""
    path = os.path.join(settings.models_dir, coin, f"{model_name}.joblib")
    if not os.path.exists(path):
        raise FileNotFoundError(f"No saved model at {path}")
    return joblib.load(path)


def load_lstm_model(coin: str):
    """Load saved LSTM model + scaler. Returns (model, scaler)."""
    import tensorflow as tf

    d = os.path.join(settings.models_dir, coin)
    model = tf.keras.models.load_model(os.path.join(d, "lstm_model"))
    scaler = joblib.load(os.path.join(d, "lstm_scaler.joblib"))
    return model, scaler
