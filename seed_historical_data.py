"""
seed_historical_data.py
-----------------------
One-time script that backfills up to 365 days of historical OHLCV data
from CoinGecko into the database.

Run this ONCE after setup — then the live pipeline takes over.

Usage
-----
    python seed_historical_data.py              # all supported coins, 365 days
    python seed_historical_data.py bitcoin 180  # bitcoin only, 180 days
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone

import requests
from loguru import logger

from config import settings
from database.db_connector import CryptoMarketData, SessionLocal, init_db

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CryptoPredictor/1.0)",
    "Accept": "application/json",
}


def fetch_historical(coin: str, days: int = 365) -> list[dict]:
    """
    Fetch daily OHLCV history from CoinGecko /coins/{id}/market_chart.
    Returns one row per day going back `days` days.
    """
    url = f"{COINGECKO_BASE}/coins/{coin}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": days,
        "interval": "daily",
    }
    if settings.coingecko_api_key:
        params["x_cg_demo_api_key"] = settings.coingecko_api_key

    resp = requests.get(url, params=params, headers=HEADERS, timeout=30)

    if resp.status_code == 429:
        wait = int(resp.headers.get("Retry-After", 60))
        logger.warning(f"Rate limited — waiting {wait}s ...")
        time.sleep(wait)
        resp = requests.get(url, params=params, headers=HEADERS, timeout=30)

    resp.raise_for_status()
    data = resp.json()

    prices      = {ts: p  for ts, p  in data.get("prices",       [])}
    volumes     = {ts: v  for ts, v  in data.get("total_volumes", [])}
    market_caps = {ts: mc for ts, mc in data.get("market_caps",   [])}

    rows = []
    for ts_ms, price in prices.items():
        timestamp = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).replace(tzinfo=None)
        rows.append({
            "coin":                 coin,
            "timestamp":            timestamp,
            "price":                float(price or 0),
            "volume":               float(volumes.get(ts_ms, 0) or 0),
            "market_cap":           float(market_caps.get(ts_ms, 0) or 0),
            "circulating_supply":   0.0,
            "change_percentage_24h": 0.0,
            "change_percentage_7d":  0.0,
        })

    return sorted(rows, key=lambda r: r["timestamp"])


def already_seeded(coin: str) -> int:
    """Return the number of rows already in the DB for this coin."""
    db = SessionLocal()
    try:
        return db.query(CryptoMarketData).filter(
            CryptoMarketData.coin == coin
        ).count()
    finally:
        db.close()


def save_rows(rows: list[dict]) -> None:
    db = SessionLocal()
    try:
        db.add_all([CryptoMarketData(**r) for r in rows])
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.error(f"DB save failed: {exc}")
        raise
    finally:
        db.close()


def seed_coin(coin: str, days: int = 365) -> None:
    existing = already_seeded(coin)
    if existing >= days * 0.8:          # already mostly seeded
        logger.info(f"[{coin}] Already has {existing} rows — skipping seed.")
        return

    logger.info(f"[{coin}] Fetching {days} days of history ...")
    try:
        rows = fetch_historical(coin, days)
        save_rows(rows)
        logger.success(f"[{coin}] Seeded {len(rows)} historical rows.")
    except Exception as exc:
        logger.error(f"[{coin}] Seed failed: {exc}")


def main() -> None:
    init_db()

    coins = settings.supported_coins
    days  = 365

    # Allow CLI overrides: python seed_historical_data.py bitcoin 180
    if len(sys.argv) >= 2:
        coins = [sys.argv[1]]
    if len(sys.argv) >= 3:
        days = int(sys.argv[2])

    logger.info(f"Seeding {len(coins)} coin(s) with {days} days of history ...")
    for i, coin in enumerate(coins):
        seed_coin(coin, days)
        # Be polite to CoinGecko free tier — 1 request/second max
        if i < len(coins) - 1:
            logger.info("Waiting 2s before next coin (rate limit) ...")
            time.sleep(2)

    logger.success("Historical seeding complete! You can now train models immediately.")
    print("\n Next steps:")
    print("   python -m ml_engine.train_model bitcoin")
    print("   python -m ml_engine.train_model ethereum")
    print("   (repeat for each coin, or train all at once)")


if __name__ == "__main__":
    main()