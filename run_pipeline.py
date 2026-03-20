"""
run_pipeline.py
---------------
Main entry point that starts the APScheduler-driven data pipeline.

Schedule
--------
Every 5 min  → fetch live data, save to DB, refresh FAISS news index
Every 1 hour → retrain all models for all supported coins
On demand    → serve predictions via the FastAPI layer

Usage
-----
    # Start just the pipeline scheduler (no HTTP server):
    python run_pipeline.py

    # Start the API server separately:
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from config import settings
from database.db_connector import init_db
from data_pipeline.fetch_data import fetch_live_data, save_market_data
from insight_engine.news_scraper import fetch_news, save_news
from insight_engine.embeddings import build_vector_store
from ml_engine.train_model import train_all_models


# ── Job Definitions ───────────────────────────────────────────────────────────

def job_fetch_and_store() -> None:
    """
    Scheduled job: fetch live prices + news, persist to DB.
    Runs every DATA_REFRESH_INTERVAL_MINUTES minutes.
    """
    logger.info("⏱  [Scheduler] Fetching live market data …")
    try:
        rows = fetch_live_data(settings.supported_coins)
        save_market_data(rows)
    except Exception as exc:
        logger.error(f"Live data fetch failed: {exc}")

    # Fetch news for each coin (non-blocking on failure)
    for coin in settings.supported_coins:
        try:
            articles = fetch_news(coin, max_articles=10)
            if articles:
                save_news(articles)
        except Exception as exc:
            logger.warning(f"News fetch failed for {coin}: {exc}")

    logger.info("✅  [Scheduler] Market data + news saved.")


def job_rebuild_embeddings() -> None:
    """
    Rebuild FAISS vector stores for all coins.
    Runs every hour alongside model retraining.
    """
    for coin in settings.supported_coins:
        try:
            build_vector_store(coin)
        except Exception as exc:
            logger.warning(f"Embedding build failed for {coin}: {exc}")


def job_retrain_models() -> None:
    """
    Scheduled job: retrain all ML models for all supported coins.
    Runs every MODEL_RETRAIN_INTERVAL_HOURS hours.
    """
    logger.info("🤖  [Scheduler] Starting model retraining …")
    for coin in settings.supported_coins:
        try:
            results = train_all_models(coin)
            for r in results:
                logger.info(
                    f"  [{coin}] {r['model_name']} — "
                    f"RMSE={r.get('rmse', '?'):.2f}"
                )
        except Exception as exc:
            logger.error(f"Model training failed for {coin}: {exc}")
    logger.info("✅  [Scheduler] Retraining complete.")


# ── Scheduler Setup ───────────────────────────────────────────────────────────

def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")

    # Fetch data every N minutes
    scheduler.add_job(
        job_fetch_and_store,
        trigger=IntervalTrigger(minutes=settings.data_refresh_interval_minutes),
        id="fetch_and_store",
        name="Live Data Fetch",
        replace_existing=True,
        max_instances=1,
    )

    # Retrain models every N hours
    scheduler.add_job(
        job_retrain_models,
        trigger=IntervalTrigger(hours=settings.model_retrain_interval_hours),
        id="retrain_models",
        name="Model Retraining",
        replace_existing=True,
        max_instances=1,
    )
    # Rebuild embeddings every hour (align with retrain)
    scheduler.add_job(
        job_rebuild_embeddings,
        trigger=IntervalTrigger(hours=1),
        id="rebuild_embeddings",
        name="FAISS Rebuild",
        replace_existing=True,
        max_instances=1,
    )

    return scheduler


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("🚀  CryptoPredictor Pipeline starting …")

    # 1. Initialise DB
    init_db()

    # 2. Run an immediate data fetch before the scheduler kicks in
    logger.info("Running initial data fetch …")
    job_fetch_and_store()

    # 3. Start scheduler
    scheduler = build_scheduler()
    scheduler.start()
    logger.info(
        f"Scheduler running — data every {settings.data_refresh_interval_minutes}m, "
        f"retraining every {settings.model_retrain_interval_hours}h"
    )

    try:
        while True:
            time.sleep(60)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("Pipeline stopped.")


if __name__ == "__main__":
    main()
