"""
data_pipeline/feature_engineering.py
--------------------------------------
Transforms cleaned OHLCV data into model-ready features.
Adapts window sizes to available data so training works even with few rows.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger


def _sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=1).mean()


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=1).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(series, fast=12, slow=26, signal=9):
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    return macd_line, signal_line, macd_line - signal_line


def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all technical features. Window sizes adapt to available data
    so this works whether you have 10 rows or 10,000.
    """
    required = {"timestamp", "price", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"feature_engineering: missing columns {missing}")

    if df.empty:
        logger.warning("feature_engineering received an empty DataFrame.")
        return df

    df = df.copy().sort_values("timestamp").reset_index(drop=True)
    n = len(df)
    price = df["price"]
    volume = df["volume"]

    # ── Moving Averages (min_periods=1 so no NaNs from short data) ────────────
    df["sma_7"]  = _sma(price, min(7,  n))
    df["sma_14"] = _sma(price, min(14, n))
    df["sma_30"] = _sma(price, min(30, n))

    df["price_above_sma7"]  = (price > df["sma_7"]).astype(int)
    df["price_above_sma30"] = (price > df["sma_30"]).astype(int)

    # ── Returns & Volatility ──────────────────────────────────────────────────
    log_returns = np.log(price / price.shift(1))
    df["log_return_1d"]  = log_returns
    df["volatility_14d"] = log_returns.rolling(window=min(14, n), min_periods=1).std()

    # ── Momentum ──────────────────────────────────────────────────────────────
    df["momentum_1d"] = price.pct_change(1)
    df["momentum_7d"] = price.pct_change(min(7, n - 1))

    # ── RSI (min_periods=1 so it works on small datasets) ────────────────────
    df["rsi_14"]       = _rsi(price, min(14, n))
    df["rsi_overbought"] = (df["rsi_14"] > 70).astype(int)
    df["rsi_oversold"]   = (df["rsi_14"] < 30).astype(int)

    # ── MACD ──────────────────────────────────────────────────────────────────
    macd_line, signal_line, histogram = _macd(price)
    df["macd"]           = macd_line
    df["macd_signal"]    = signal_line
    df["macd_histogram"] = histogram

    # ── Volume Features ───────────────────────────────────────────────────────
    vol_window = min(7, n)
    df["volume_sma_7"] = _sma(volume, vol_window)
    vol_std  = volume.rolling(window=vol_window, min_periods=1).std()
    vol_mean = volume.rolling(window=vol_window, min_periods=1).mean()
    df["volume_zscore"] = (volume - vol_mean) / vol_std.replace(0, np.nan)
    df["volume_spike"]  = (df["volume_zscore"].abs() > 2).astype(int)

    # ── Lag Features ─────────────────────────────────────────────────────────
    for lag in [1, 3, 7]:
        df[f"price_lag_{lag}"] = price.shift(min(lag, n - 1))

    # ── Target ────────────────────────────────────────────────────────────────
    df["target_price_next"] = price.shift(-1)

    # ── Drop only the last row (no target) — keep everything else ─────────────
    before = len(df)
    df = df.dropna(subset=["target_price_next"])
    df = df.fillna(method="ffill").fillna(method="bfill").fillna(0)
    df = df.reset_index(drop=True)

    logger.info(
        f"Feature engineering complete: {before} → {len(df)} rows, "
        f"{len(df.columns)} columns"
    )
    return df


FEATURE_COLUMNS: list[str] = [
    "sma_7", "sma_14", "sma_30",
    "price_above_sma7", "price_above_sma30",
    "log_return_1d", "volatility_14d",
    "momentum_1d", "momentum_7d",
    "rsi_14", "rsi_overbought", "rsi_oversold",
    "macd", "macd_signal", "macd_histogram",
    "volume_sma_7", "volume_zscore", "volume_spike",
    "price_lag_1", "price_lag_3", "price_lag_7",
]