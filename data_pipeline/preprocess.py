"""
data_pipeline/preprocess.py
----------------------------
Loads raw market data from the database and cleans it for modelling.

Public API
----------
clean_market_data(coin, lookback_days) → pd.DataFrame
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
from loguru import logger
from sqlalchemy import select

from database.db_connector import CryptoMarketData, SessionLocal


def clean_market_data(
    coin: str,
    lookback_days: int = 90,
) -> pd.DataFrame:
    """
    Load and clean raw market data for a single coin.

    Steps
    -----
    1. Query the last `lookback_days` from the database
    2. Drop rows with missing price / volume
    3. Remove duplicate timestamps (keep latest fetch)
    4. Sort chronologically
    5. Forward-fill any remaining gaps in non-price columns

    Parameters
    ----------
    coin : str
        CoinGecko slug, e.g. "bitcoin"
    lookback_days : int
        How many days of history to load (default 90)

    Returns
    -------
    pd.DataFrame
        Cleaned, sorted DataFrame indexed by timestamp.
    """
    logger.info(f"Loading {lookback_days}d of data for {coin} …")

    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
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
        rows = db.execute(stmt).scalars().all()
    finally:
        db.close()

    if not rows:
        logger.warning(f"No data found for {coin} — returning empty DataFrame.")
        return pd.DataFrame()

    df = pd.DataFrame(
        [
            {
                "timestamp": r.timestamp,
                "price": r.price,
                "volume": r.volume,
                "market_cap": r.market_cap,
                "circulating_supply": r.circulating_supply,
                "change_pct_24h": r.change_percentage_24h,
                "change_pct_7d": r.change_percentage_7d,
            }
            for r in rows
        ]
    )

    # ── Clean ──────────────────────────────────────────────────────────────────
    initial_len = len(df)

    # Drop rows where price or volume are zero / null (unusable)
    df = df.dropna(subset=["price", "volume"])
    df = df[df["price"] > 0]

    # Remove duplicates — keep last record per timestamp minute
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp")
    df = df.drop_duplicates(subset=["timestamp"], keep="last")

    # Forward-fill secondary columns
    df[["market_cap", "circulating_supply"]] = (
        df[["market_cap", "circulating_supply"]].ffill()
    )

    df = df.reset_index(drop=True)

    logger.info(
        f"Cleaned {coin}: {initial_len} → {len(df)} rows "
        f"({initial_len - len(df)} dropped)"
    )
    return df
