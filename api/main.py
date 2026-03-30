"""
api/main.py
-----------
FastAPI application exposing the crypto prediction platform.

Start the server
----------------
    uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

Swagger UI  →  http://localhost:8000/docs
ReDoc       →  http://localhost:8000/redoc
"""

from __future__ import annotations

from typing import Any

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from sqlalchemy.orm import Session

from config import settings
from database.db_connector import get_db, init_db
from data_pipeline.fetch_data import fetch_live_data
from insight_engine.rag_pipeline import generate_market_insight
from prediction_service.predictor import predict_price, save_prediction
from visualization.chart_generator import (
    generate_heatmap_data,
    generate_market_share_data,
    generate_price_chart_data,
    generate_volume_spike_data,
)

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend" / "dist"


# ── App Setup ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CryptoPredictor API",
    description="Live crypto data, ML predictions, and RAG insights.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.on_event("startup")
async def startup_event():
    logger.info("Initialising database …")
    init_db()
    logger.info("CryptoPredictor API ready.")


# ── Validation ────────────────────────────────────────────────────────────────

def _validate_coin(coin: str) -> str:
    coin = coin.lower()
    if coin not in settings.supported_coins:
        raise HTTPException(
            status_code=404,
            detail=f"Coin '{coin}' not supported. Choose from: {settings.supported_coins}",
        )
    return coin


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root() -> dict:
    return {"status": "ok", "service": "CryptoPredictor", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health() -> dict:
    return {"status": "healthy"}


@app.get("/app", include_in_schema=False)
def dashboard() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard assets missing.")
    return FileResponse(index_path)


# ── 1. Live Data ───────────────────────────────────────────────────────────────

@app.get("/live-data/{coin}", tags=["Market Data"])
def get_live_data(coin: str) -> dict[str, Any]:
    """
    Fetch the latest live market data for a single coin.

    Returns price, volume, market_cap, 24h change, and more.
    """
    coin = _validate_coin(coin)
    try:
        rows = fetch_live_data([coin])
        if not rows:
            raise HTTPException(status_code=503, detail="Failed to fetch live data.")
        return {"status": "success", "data": rows[0]}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"/live-data/{coin} error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/live-data", tags=["Market Data"])
def get_all_live_data() -> dict[str, Any]:
    """Fetch live data for all supported coins."""
    try:
        rows = fetch_live_data(settings.supported_coins)
        return {"status": "success", "count": len(rows), "data": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── 2. Predictions ─────────────────────────────────────────────────────────────

@app.get("/prediction/{coin}", tags=["Predictions"])
def get_prediction(
    coin: str,
    model: str = Query(default="xgboost", enum=["xgboost", "random_forest", "lstm"]),
) -> dict[str, Any]:
    """
    Generate a next-price prediction for the given coin.

    Query params
    ------------
    model : str  (default: xgboost)
        Which ML model to use: xgboost | random_forest | lstm
    """
    coin = _validate_coin(coin)
    try:
        result = predict_price(coin, model_name=model)
        save_prediction(result)
        return {"status": "success", "data": result.to_dict()}
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No trained model found for {coin}/{model}. Train it first.",
        )
    except Exception as exc:
        logger.error(f"/prediction/{coin} error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ── 3. Insights ────────────────────────────────────────────────────────────────

@app.get("/insights/{coin}", tags=["Insights"])
def get_insights(coin: str) -> dict[str, Any]:
    """
    Generate a RAG-powered explanation of why the coin price moved.

    Internally:
    1. Retrieves a fresh price prediction
    2. Retrieves top-k relevant news via FAISS
    3. Asks GPT to synthesise an insight
    """
    coin = _validate_coin(coin)
    try:
        prediction = predict_price(coin, model_name="xgboost")
        insight = generate_market_insight(
            coin=coin,
            current_price=prediction.current_price,
            predicted_price=prediction.predicted_price,
            trend=prediction.trend,
        )
        return {
            "status": "success",
            "coin": coin,
            "trend": prediction.trend,
            "current_price": prediction.current_price,
            "predicted_price": prediction.predicted_price,
            "insight": insight,
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No trained model for {coin}. Run training first.",
        )
    except Exception as exc:
        logger.error(f"/insights/{coin} error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ── 4. Visualizations ──────────────────────────────────────────────────────────

@app.get("/visualizations/{coin}", tags=["Visualizations"])
def get_visualizations(
    coin: str,
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    """
    Retrieve chart data bundles for a coin.

    Returns price/SMA/RSI/MACD line-chart data, volume spike markers,
    and model prediction overlays.
    """
    coin = _validate_coin(coin)
    try:
        return {
            "status": "success",
            "price_chart": generate_price_chart_data(coin, days=days),
            "volume_spikes": generate_volume_spike_data(coin, days=days),
        }
    except Exception as exc:
        logger.error(f"/visualizations/{coin} error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/visualizations/market/heatmap", tags=["Visualizations"])
def get_heatmap(days: int = Query(default=7, ge=1, le=30)) -> dict[str, Any]:
    """7-day price change heatmap across all supported coins."""
    try:
        return {"status": "success", "data": generate_heatmap_data(days=days)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/visualizations/market/dominance", tags=["Visualizations"])
def get_market_dominance() -> dict[str, Any]:
    """Market-cap dominance pie-chart data."""
    try:
        return {"status": "success", "data": generate_market_share_data()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
