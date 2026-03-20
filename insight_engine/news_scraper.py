"""
insight_engine/news_scraper.py
-------------------------------
Scrapes cryptocurrency news from free sources (CoinDesk RSS, CryptoPanic API).

Public API
----------
fetch_news(coin, max_articles) → list[dict]
save_news(articles)            → None
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

import requests
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from database.db_connector import NewsData, SessionLocal


# ── CoinDesk RSS ──────────────────────────────────────────────────────────────

RSS_FEEDS = {
    "bitcoin": "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
    "ethereum": "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
    "default": "https://www.coindesk.com/arc/outboundfeeds/rss/?outputType=xml",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
def _fetch_rss(coin: str) -> list[dict]:
    url = RSS_FEEDS.get(coin, RSS_FEEDS["default"])
    resp = requests.get(url, timeout=15, headers={"User-Agent": "CryptoPredictor/1.0"})
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    channel = root.find("channel")
    if channel is None:
        return []

    articles = []
    for item in channel.findall("item"):
        title = item.findtext("title", "")
        description = item.findtext("description", "")
        link = item.findtext("link", "")
        pub_date_str = item.findtext("pubDate", "")

        # Only keep articles that mention the coin
        search_terms = _coin_search_terms(coin)
        full_text = f"{title} {description}".lower()
        if not any(term in full_text for term in search_terms):
            continue

        try:
            from email.utils import parsedate_to_datetime
            pub_date = parsedate_to_datetime(pub_date_str).replace(tzinfo=None)
        except Exception:
            pub_date = datetime.utcnow()

        articles.append({
            "coin": coin,
            "headline": title.strip(),
            "summary": description.strip()[:500],
            "source": "CoinDesk",
            "url": link.strip(),
            "timestamp": pub_date,
        })

    return articles


def _coin_search_terms(coin: str) -> list[str]:
    """Map coin slug to keywords to filter relevant news."""
    mapping = {
        "bitcoin": ["bitcoin", "btc"],
        "ethereum": ["ethereum", "eth"],
        "solana": ["solana", "sol"],
        "binancecoin": ["binance", "bnb"],
        "ripple": ["ripple", "xrp"],
    }
    return mapping.get(coin, [coin])


# ── CryptoPanic (optional) ────────────────────────────────────────────────────

def _fetch_cryptopanic(coin: str, api_key: str, max_articles: int) -> list[dict]:
    """
    Fetch from CryptoPanic public API.
    Requires a free API key from https://cryptopanic.com/developers/api/
    """
    ticker_map = {
        "bitcoin": "BTC", "ethereum": "ETH",
        "solana": "SOL", "binancecoin": "BNB", "ripple": "XRP",
    }
    ticker = ticker_map.get(coin, coin.upper())
    url = "https://cryptopanic.com/api/v1/posts/"
    params = {
        "auth_token": api_key,
        "currencies": ticker,
        "kind": "news",
        "public": "true",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("results", [])[:max_articles]
        return [
            {
                "coin": coin,
                "headline": i.get("title", ""),
                "summary": "",
                "source": i.get("source", {}).get("title", "CryptoPanic"),
                "url": i.get("url", ""),
                "timestamp": datetime.utcnow(),
            }
            for i in items
        ]
    except Exception as exc:
        logger.warning(f"CryptoPanic fetch failed: {exc}")
        return []


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_news(coin: str, max_articles: int = 20) -> list[dict]:
    """
    Fetch news articles relevant to a coin.

    Parameters
    ----------
    coin : str
        CoinGecko slug.
    max_articles : int
        Maximum number of articles to return.

    Returns
    -------
    list[dict]
        Articles with keys: coin, headline, summary, source, url, timestamp.
    """
    articles: list[dict] = []

    try:
        rss_articles = _fetch_rss(coin)
        articles.extend(rss_articles)
        logger.info(f"Fetched {len(rss_articles)} articles from RSS for {coin}")
    except Exception as exc:
        logger.warning(f"RSS fetch failed for {coin}: {exc}")

    return articles[:max_articles]


def save_news(articles: list[dict]) -> None:
    """Persist fetched news articles to the database."""
    if not articles:
        return
    db = SessionLocal()
    try:
        db.add_all([NewsData(**a) for a in articles])
        db.commit()
        logger.info(f"Saved {len(articles)} news articles.")
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to save news: {exc}")
    finally:
        db.close()
