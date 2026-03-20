"""
visualization/chart_generator.py
----------------------------------
Generates JSON-serialisable payloads for frontend charts.

Public API
----------
generate_price_chart_data(coin, days)  → dict
generate_heatmap_data(coins)           → dict
generate_market_share_data(coins)      → dict
generate_volume_spike_data(coin, days) → dict
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import numpy as np
from loguru import logger
from sqlalchemy import select

from config import settings
from database.db_connector import CryptoMarketData, ModelPrediction, SessionLocal
from data_pipeline.feature_engineering import feature_engineering
from data_pipeline.preprocess import clean_market_data


# ── Helpers ───────────────────────────────────────────────────────────────────

def _query_market(coin: str, days: int) -> list[CryptoMarketData]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    db = SessionLocal()
    try:
        stmt = (
            select(CryptoMarketData)
            .where(
                CryptoMarketData.coin == coin,
                CryptoMarketData.timestamp >= cutoff,
            )
            .order_by(CryptoMarketData.timestamp)
        )
        return db.execute(stmt).scalars().all()
    finally:
        db.close()


# ── Chart generators ─────────────────────────────────────────────────────────

def generate_price_chart_data(
    coin: str,
    days: int = 30,
) -> dict[str, Any]:
    """
    Build a line-chart payload for the given coin.

    Returns
    -------
    dict
        {
          "coin": str,
          "labels": [ISO timestamps],
          "price": [float],
          "sma_7": [float],
          "sma_30": [float],
          "predicted": [{"timestamp": ..., "price": ...}]
        }
    """
    rows = _query_market(coin, days)
    if not rows:
        return {"coin": coin, "labels": [], "price": [], "sma_7": [], "sma_30": []}

    raw = clean_market_data(coin, lookback_days=days)
    if raw.empty:
        return {"coin": coin, "labels": [], "price": []}

    df = feature_engineering(raw)

    # Recent model predictions
    db = SessionLocal()
    cutoff = datetime.utcnow() - timedelta(days=days)
    try:
        preds = (
            db.execute(
                select(ModelPrediction)
                .where(
                    ModelPrediction.coin == coin,
                    ModelPrediction.prediction_time >= cutoff,
                )
                .order_by(ModelPrediction.prediction_time)
            )
            .scalars()
            .all()
        )
    finally:
        db.close()

    return {
        "coin": coin,
        "labels": df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S").tolist(),
        "price": df["price"].round(4).tolist(),
        "sma_7": df["sma_7"].round(4).tolist(),
        "sma_30": df["sma_30"].round(4).tolist(),
        "rsi": df["rsi_14"].round(2).tolist() if "rsi_14" in df.columns else [],
        "macd": df["macd"].round(4).tolist() if "macd" in df.columns else [],
        "predicted": [
            {
                "timestamp": p.prediction_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "price": round(p.predicted_price, 4),
                "model": p.model_name,
            }
            for p in preds
        ],
    }


def generate_heatmap_data(
    coins: list[str] | None = None,
    days: int = 7,
) -> dict[str, Any]:
    """
    Build a heatmap payload of 7-day price changes per coin.

    Returns
    -------
    dict
        {"coins": [...], "change_pct_7d": [...], "heatmap": [[...]]}
    """
    if coins is None:
        coins = settings.supported_coins

    results = []
    for coin in coins:
        rows = _query_market(coin, days)
        if len(rows) < 2:
            change = 0.0
        else:
            first, last = rows[0].price, rows[-1].price
            change = round((last - first) / (first or 1) * 100, 2)
        results.append({"coin": coin, "change_pct": change})

    return {
        "coins": [r["coin"] for r in results],
        "change_pct_7d": [r["change_pct"] for r in results],
        # 2-D matrix for heatmap (coins × 1 metric here; extend as needed)
        "heatmap": [[r["change_pct"]] for r in results],
    }


def generate_market_share_data(
    coins: list[str] | None = None,
) -> dict[str, Any]:
    """
    Build a pie/donut chart payload of current market-cap dominance.

    Returns
    -------
    dict
        {"labels": [...], "market_caps": [...], "dominance_pct": [...]}
    """
    if coins is None:
        coins = settings.supported_coins

    db = SessionLocal()
    labels, caps = [], []

    try:
        for coin in coins:
            # Latest market cap
            stmt = (
                select(CryptoMarketData.market_cap)
                .where(CryptoMarketData.coin == coin)
                .order_by(CryptoMarketData.timestamp.desc())
                .limit(1)
            )
            result = db.execute(stmt).scalar_one_or_none()
            if result:
                labels.append(coin)
                caps.append(result)
    finally:
        db.close()

    total = sum(caps) or 1
    dominance = [round(c / total * 100, 2) for c in caps]

    return {
        "labels": labels,
        "market_caps": [round(c, 0) for c in caps],
        "dominance_pct": dominance,
    }


def generate_volume_spike_data(
    coin: str,
    days: int = 14,
) -> dict[str, Any]:
    """
    Identify and return volume spike events for a coin.

    Returns
    -------
    dict
        {"timestamps": [...], "volume": [...], "spikes": [...bool...]}
    """
    raw = clean_market_data(coin, lookback_days=days)
    if raw.empty:
        return {"coin": coin, "timestamps": [], "volume": [], "spikes": []}

    df = feature_engineering(raw)

    return {
        "coin": coin,
        "timestamps": df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S").tolist(),
        "volume": df["volume"].round(0).tolist(),
        "volume_zscore": df.get("volume_zscore", []).round(3).tolist()
        if "volume_zscore" in df.columns
        else [],
        "spikes": df["volume_spike"].tolist() if "volume_spike" in df.columns else [],
    }
