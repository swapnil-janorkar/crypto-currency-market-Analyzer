"""
data_pipeline/fetch_data.py
---------------------------
Fetches live market data from CoinGecko and Binance APIs with retry logic,
then persists raw rows into the database.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from database.db_connector import CryptoMarketData, SessionLocal

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CryptoPredictor/1.0)",
    "Accept": "application/json",
}


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=5, max=60))
def _fetch_coingecko_markets(coin_ids: list[str]) -> list[dict[str, Any]]:
    """Full /coins/markets endpoint with rate-limit handling."""
    params: dict[str, Any] = {
        "vs_currency": "usd",
        "ids": ",".join(coin_ids),
        "order": "market_cap_desc",
        "per_page": 50,
        "page": 1,
        "sparkline": False,
        "price_change_percentage": "1h,24h,7d",
    }
    if settings.coingecko_api_key:
        params["x_cg_demo_api_key"] = settings.coingecko_api_key

    resp = requests.get(
        f"{COINGECKO_BASE}/coins/markets",
        params=params,
        headers=_HEADERS,
        timeout=30,
    )

    if resp.status_code == 429:
        wait = int(resp.headers.get("Retry-After", 60))
        logger.warning(f"CoinGecko rate-limited — waiting {wait}s ...")
        time.sleep(wait)
        resp.raise_for_status()

    resp.raise_for_status()
    return resp.json()


def _fetch_coingecko_simple(coin_ids: list[str]) -> list[dict[str, Any]]:
    """
    Fallback: /simple/price — lighter endpoint, less rate-limited.
    Returns items shaped like /coins/markets so the parser works unchanged.
    """
    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": "usd",
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
    }
    resp = requests.get(
        f"{COINGECKO_BASE}/simple/price",
        params=params,
        headers=_HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    return [
        {
            "id": coin_id,
            "current_price": v.get("usd", 0),
            "market_cap": v.get("usd_market_cap", 0),
            "total_volume": v.get("usd_24h_vol", 0),
            "circulating_supply": 0,
            "price_change_percentage_24h": v.get("usd_24h_change", 0),
            "price_change_percentage_7d_in_currency": 0,
        }
        for coin_id, v in data.items()
    ]


def _parse_row(item: dict[str, Any]) -> dict[str, Any]:
    """Flatten a CoinGecko item into our standard DB schema."""
    return {
        "coin": item["id"],
        "timestamp": datetime.utcnow(),
        "price": float(item.get("current_price") or 0),
        "volume": float(item.get("total_volume") or 0),
        "market_cap": float(item.get("market_cap") or 0),
        "circulating_supply": float(item.get("circulating_supply") or 0),
        "change_percentage_24h": float(item.get("price_change_percentage_24h") or 0),
        "change_percentage_7d": float(
            item.get("price_change_percentage_7d_in_currency") or 0
        ),
    }


# ── Binance ───────────────────────────────────────────────────────────────────

BINANCE_BASE = "https://api.binance.com/api/v3"
BINANCE_SYMBOL_MAP: dict[str, str] = {
    "bitcoin": "BTCUSDT",
    "ethereum": "ETHUSDT",
    "solana": "SOLUSDT",
    "binancecoin": "BNBUSDT",
    "ripple": "XRPUSDT",
}


def _fetch_binance_price(symbol: str) -> float | None:
    try:
        resp = requests.get(
            f"{BINANCE_BASE}/ticker/price",
            params={"symbol": symbol},
            timeout=10,
        )
        resp.raise_for_status()
        return float(resp.json()["price"])
    except Exception as exc:
        logger.debug(f"Binance price fetch skipped for {symbol}: {exc}")
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_live_data(coins: list[str] | None = None) -> list[dict[str, Any]]:
    """
    Fetch live market data. Tries /coins/markets first, falls back to
    /simple/price if rate-limited, then cross-checks price with Binance.
    """
    if coins is None:
        coins = settings.supported_coins

    logger.info(f"Fetching live data for {coins} ...")

    # Try full endpoint, fall back to simple price
    try:
        raw = _fetch_coingecko_markets(coins)
        logger.debug("Used /coins/markets endpoint.")
    except Exception as exc:
        logger.warning(f"/coins/markets failed ({exc}) — falling back to /simple/price")
        try:
            raw = _fetch_coingecko_simple(coins)
            logger.debug("Used /simple/price fallback.")
        except Exception as exc2:
            logger.error(f"Both CoinGecko endpoints failed: {exc2}")
            return []

    rows: list[dict[str, Any]] = []
    for item in raw:
        row = _parse_row(item)
        sym = BINANCE_SYMBOL_MAP.get(item["id"])
        if sym:
            binance_price = _fetch_binance_price(sym)
            if binance_price:
                row["price"] = binance_price
        rows.append(row)

    logger.success(f"Fetched {len(rows)} coins successfully.")
    return rows


def save_market_data(rows: list[dict[str, Any]]) -> None:
    """Persist a list of market data rows to the database."""
    if not rows:
        logger.warning("save_market_data called with empty list — nothing saved.")
        return

    db = SessionLocal()
    try:
        db.add_all([CryptoMarketData(**row) for row in rows])
        db.commit()
        logger.info(f"Saved {len(rows)} rows to crypto_market_data.")
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to save market data: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    rows = fetch_live_data(["bitcoin", "ethereum"])
    for r in rows:
        print(r)