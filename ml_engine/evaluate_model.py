"""
ml_engine/evaluate_model.py
----------------------------
Model evaluation utilities (RMSE, MAE, R², directional accuracy).

Public API
----------
evaluate_regression(model, X_test, y_test) → dict[str, float]
directional_accuracy(y_true, y_pred)       → float
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score


def evaluate_regression(
    model,
    X_test: pd.DataFrame | np.ndarray,
    y_test: pd.Series | np.ndarray,
) -> dict[str, float]:
    """
    Compute standard regression metrics.

    Parameters
    ----------
    model
        Any sklearn-compatible model with a .predict() method.
    X_test, y_test
        Hold-out test data.

    Returns
    -------
    dict
        {rmse, mae, r2, directional_accuracy}
    """
    y_pred = model.predict(X_test)
    y_true = np.array(y_test)

    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    da = directional_accuracy(y_true, y_pred)

    return {"rmse": rmse, "mae": mae, "r2": r2, "directional_accuracy": da}


def directional_accuracy(
    y_true: np.ndarray,
    y_pred: np.ndarray,
) -> float:
    """
    Percentage of timesteps where model correctly predicted direction.

    Parameters
    ----------
    y_true, y_pred : np.ndarray
        Actual and predicted price arrays.

    Returns
    -------
    float
        Value in [0, 1].
    """
    if len(y_true) < 2:
        return 0.0
    actual_dir = np.sign(np.diff(y_true))
    predicted_dir = np.sign(np.diff(y_pred))
    return float(np.mean(actual_dir == predicted_dir))
