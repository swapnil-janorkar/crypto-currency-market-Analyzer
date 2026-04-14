# CryptoPredictor — Neural Market Intelligence Platform

> A production-ready cryptocurrency prediction system powered by live market data, ensemble machine learning (RandomForest, XGBoost, LSTM), a RAG-based insight engine, and a FastAPI backend — all automated via APScheduler.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Database Setup](#database-setup)
- [Seeding Historical Data](#seeding-historical-data)
- [Data Pipeline](#data-pipeline)
- [Feature Engineering](#feature-engineering)
- [ML Engine](#ml-engine)
- [Prediction Service](#prediction-service)
- [RAG Insight Engine](#rag-insight-engine)
- [Visualization Layer](#visualization-layer)
- [API Reference](#api-reference)
- [Scheduler & Automation](#scheduler--automation)
- [Running the System](#running-the-system)
- [Supported Coins](#supported-coins)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

CryptoPredictor is a full end-to-end machine learning platform for cryptocurrency price prediction. It was built to solve the cold-start and real-time data problem in crypto ML — instead of downloading CSVs manually, the system:

1. **Fetches live price data** from CoinGecko and Binance every 5 minutes
2. **Seeds 365 days of historical data** on first run so models are useful immediately
3. **Engineers 21 technical indicators** (RSI, MACD, Bollinger-adjacent features, volume spikes)
4. **Trains three model types** — RandomForest, XGBoost, and LSTM — which retrain automatically every hour
5. **Explains price moves** using a RAG pipeline that scrapes financial news, embeds it in FAISS, and queries GPT
6. **Exposes everything via FastAPI** with 7 JSON endpoints ready for any frontend

The system is designed to run continuously on a local machine or server with zero manual intervention after the first setup.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SCHEDULER (APScheduler)                  │
│   Every 5 min: fetch data → save to DB → scrape news            │
│   Every 1 hr:  retrain models → rebuild FAISS index             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
           ┌────────────────▼────────────────┐
           │         DATA PIPELINE            │
           │  CoinGecko API  +  Binance API   │
           │  fetch → clean → feature engineer│
           └────────────────┬────────────────┘
                            │
           ┌────────────────▼────────────────┐
           │         DATABASE (SQLite/PG)     │
           │  crypto_market_data              │
           │  model_predictions               │
           │  news_data                       │
           └────┬──────────────────┬──────────┘
                │                  │
   ┌────────────▼───┐    ┌─────────▼──────────┐
   │   ML ENGINE    │    │   INSIGHT ENGINE    │
   │  RandomForest  │    │  News scraper (RSS) │
   │  XGBoost       │    │  OpenAI embeddings  │
   │  LSTM          │    │  FAISS vector store │
   └────────┬───────┘    │  LangChain RAG      │
            │            └─────────┬──────────┘
   ┌────────▼───────────────────────▼──────────┐
   │              FASTAPI SERVER                │
   │  /live-data  /prediction  /insights        │
   │  /visualizations  /heatmap  /dominance     │
   └────────────────────────────────────────────┘
```

---

## Project Structure

```
crypto_predictor/
│
├── data_pipeline/
│   ├── __init__.py
│   ├── fetch_data.py          # CoinGecko + Binance live fetch with fallback
│   ├── preprocess.py          # Clean, deduplicate, forward-fill raw rows
│   └── feature_engineering.py # 21 technical indicators + lag features
│
├── ml_engine/
│   ├── __init__.py
│   ├── train_model.py         # RF, XGBoost, LSTM trainers
│   ├── evaluate_model.py      # RMSE, MAE, R², directional accuracy
│   └── save_model.py          # joblib + Keras SavedModel helpers
│
├── prediction_service/
│   ├── __init__.py
│   └── predictor.py           # Load model → predict price, confidence, trend
│
├── insight_engine/
│   ├── __init__.py
│   ├── news_scraper.py        # CoinDesk RSS scraper with coin-keyword filter
│   ├── embeddings.py          # OpenAI embeddings → FAISS index builder
│   └── rag_pipeline.py        # LangChain LCEL chain → GPT-4o-mini insight
│
├── visualization/
│   ├── __init__.py
│   └── chart_generator.py     # JSON payloads for price, RSI, MACD, heatmap
│
├── database/
│   ├── __init__.py
│   └── db_connector.py        # SQLAlchemy ORM models + session factory
│
├── api/
│   ├── __init__.py
│   └── main.py                # FastAPI app with 7 endpoints
│
├── models/                    # Saved model files (auto-created)
│   └── bitcoin/
│       ├── random_forest.joblib
│       ├── xgboost.joblib
│       ├── lstm_model/        # Keras SavedModel format
│       ├── lstm_scaler.joblib
│       └── lstm_look_back.joblib
│
├── data/                      # SQLite DB + FAISS indexes (auto-created)
│   ├── crypto.db
│   └── faiss_index/
│       └── bitcoin/
│
├── logs/                      # Log output (auto-created)
│
├── config.py                  # Pydantic settings — reads from .env
├── run_pipeline.py            # APScheduler entry point
├── seed_historical_data.py    # One-time historical backfill script
├── setup.py                   # Bootstrap script (DB init + first fetch)
├── requirements.txt
├── .env.example
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI + Uvicorn |
| Database ORM | SQLAlchemy 2.0 |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ML — Classical | scikit-learn (RandomForest), XGBoost |
| ML — Deep Learning | TensorFlow / Keras (LSTM) |
| Model Persistence | joblib, Keras SavedModel |
| RAG Pipeline | LangChain (LCEL), FAISS, OpenAI |
| News Scraping | requests + xml.etree (RSS) |
| Scheduling | APScheduler |
| Data Processing | pandas, numpy |
| Retry Logic | tenacity |
| Logging | loguru |
| Config | pydantic-settings |

---

## Installation

### Prerequisites

- Python 3.10 or higher
- Node.js (only needed if running the frontend separately)
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-username/crypto-predictor.git
cd crypto-predictor/crypto_predictor

# 2. Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Copy the example environment file and edit it:

```bash
cp .env.example .env
```

Open `.env` and configure:

```env
# ── Database ─────────────────────────────────────────────────────────────────
# SQLite — zero setup, recommended for local development
DATABASE_URL=sqlite:///./data/crypto.db

# PostgreSQL — for production deployments
# DATABASE_URL=postgresql://user:password@localhost:5432/crypto_predictor

# ── External APIs ─────────────────────────────────────────────────────────────
COINGECKO_API_KEY=          # Optional — free tier works without a key
BINANCE_API_KEY=            # Optional — only needed for authenticated endpoints
BINANCE_SECRET_KEY=

# ── OpenAI (required for AI-powered market insights) ──────────────────────────
OPENAI_API_KEY=sk-...

# ── App Settings ──────────────────────────────────────────────────────────────
DATA_REFRESH_INTERVAL_MINUTES=5
MODEL_RETRAIN_INTERVAL_HOURS=1
LOG_LEVEL=INFO

# Comma-separated CoinGecko slugs — add any coin from coingecko.com
SUPPORTED_COINS_RAW=bitcoin,ethereum,solana,binancecoin,ripple
```

> **Note:** `OPENAI_API_KEY` is only required for the `/insights` endpoint. All other endpoints work without it.

---

## Database Setup

Run the one-time bootstrap script:

```bash
python setup.py
```

This will:
- Create `.env` from `.env.example` if it doesn't exist
- Create the `models/`, `data/`, and `logs/` directories
- Initialise all database tables via SQLAlchemy `create_all()`
- Run an initial live data fetch to verify API connectivity

### Database Schema

**`crypto_market_data`** — raw market snapshots fetched every 5 minutes

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `coin` | VARCHAR(50) | CoinGecko slug (e.g. `bitcoin`) |
| `timestamp` | DATETIME | UTC fetch time |
| `price` | FLOAT | Current price in USD |
| `volume` | FLOAT | 24h trading volume |
| `market_cap` | FLOAT | Total market capitalisation |
| `circulating_supply` | FLOAT | Circulating token supply |
| `change_percentage_24h` | FLOAT | 24h price change % |
| `change_percentage_7d` | FLOAT | 7d price change % |

**`model_predictions`** — stored model outputs

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `coin` | VARCHAR(50) | CoinGecko slug |
| `model_name` | VARCHAR(50) | `random_forest`, `xgboost`, or `lstm` |
| `predicted_price` | FLOAT | Forecasted next-interval price |
| `confidence` | FLOAT | Confidence score 0–1 |
| `trend` | ENUM | `bullish`, `bearish`, or `neutral` |
| `prediction_time` | DATETIME | When prediction was made |
| `target_time` | DATETIME | Which future interval is predicted |

**`news_data`** — scraped headlines for RAG context

| Column | Type | Description |
|---|---|---|
| `id` | INTEGER PK | Auto-increment |
| `coin` | VARCHAR(50) | CoinGecko slug |
| `headline` | TEXT | Article title |
| `summary` | TEXT | First 500 chars of article body |
| `source` | VARCHAR(200) | Publisher name |
| `url` | TEXT | Original article URL |
| `timestamp` | DATETIME | Publish or scrape time |

---

## Seeding Historical Data

The pipeline only collects new data every 5 minutes. Without seeding, you would need to wait weeks before having enough data to train meaningful models. The seed script backfills up to 365 days of daily OHLCV data from CoinGecko instantly:

```bash
# Seed all supported coins (365 days)
python seed_historical_data.py

# Seed a specific coin with custom lookback
python seed_historical_data.py bitcoin 180
```

**What it fetches:** CoinGecko `/coins/{id}/market_chart` with `interval=daily`. This provides price, volume, and market cap per day for each coin.

**Rate limiting:** The script waits 2 seconds between coins to stay within CoinGecko's free tier limits (30 calls/minute). For 5 coins this completes in approximately 15 seconds.

**Idempotent:** If a coin already has ≥80% of the requested days in the database, it skips that coin to avoid duplicate rows.

---

## Data Pipeline

### `data_pipeline/fetch_data.py`

Fetches live prices using a two-endpoint strategy:

1. **Primary:** `GET /coins/markets` — returns full market data including 7d change, circulating supply, and volume. Used when available.
2. **Fallback:** `GET /simple/price` — a lighter endpoint with lower rate limits. Used automatically when the primary endpoint returns HTTP 429.

Both endpoints are cross-checked with **Binance** ticker prices for the 5 default coins. Binance prices have lower latency and are used to override the CoinGecko price when available.

Retry logic uses `tenacity` with exponential backoff: 5 attempts, 5s → 10s → 20s → 40s → 60s between retries. HTTP 429 responses trigger a `time.sleep()` equal to the `Retry-After` header value before the next attempt.

```python
from data_pipeline.fetch_data import fetch_live_data, save_market_data

rows = fetch_live_data(['bitcoin', 'ethereum'])
save_market_data(rows)
```

### `data_pipeline/preprocess.py`

Loads raw data from the database and applies:

- Drop rows where `price = 0` or `price` is null
- Remove duplicate timestamps (keeps the latest fetch for each minute)
- Sort chronologically
- Forward-fill `market_cap` and `circulating_supply` gaps

```python
from data_pipeline.preprocess import clean_market_data

df = clean_market_data('bitcoin', lookback_days=90)
```

---

## Feature Engineering

`data_pipeline/feature_engineering.py` computes 21 features on top of the cleaned OHLCV data. All rolling windows use `min_periods=1` so they work correctly even with small datasets.

| Feature | Formula / Description |
|---|---|
| `sma_7`, `sma_14`, `sma_30` | Simple moving average over 7, 14, 30 periods |
| `price_above_sma7` | Binary: 1 if price > SMA-7 |
| `price_above_sma30` | Binary: 1 if price > SMA-30 |
| `log_return_1d` | `ln(price_t / price_{t-1})` |
| `volatility_14d` | Rolling 14-period std of log returns |
| `momentum_1d` | `(price_t - price_{t-1}) / price_{t-1}` |
| `momentum_7d` | 7-period percentage change |
| `rsi_14` | Wilder RSI over 14 periods |
| `rsi_overbought` | Binary: 1 if RSI > 70 |
| `rsi_oversold` | Binary: 1 if RSI < 30 |
| `macd` | EMA(12) − EMA(26) |
| `macd_signal` | EMA(9) of MACD line |
| `macd_histogram` | MACD − Signal |
| `volume_sma_7` | 7-period rolling mean of volume |
| `volume_zscore` | Z-score of volume over 7-period window |
| `volume_spike` | Binary: 1 if `\|z-score\| > 2` |
| `price_lag_1`, `price_lag_3`, `price_lag_7` | Price shifted by 1, 3, 7 periods |

**Target variable:** `target_price_next` — the price at `t+1` (next interval). This is what all models predict.

```python
from data_pipeline.feature_engineering import feature_engineering, FEATURE_COLUMNS

df_features = feature_engineering(df_clean)
X = df_features[FEATURE_COLUMNS]
y = df_features['target_price_next']
```

---

## ML Engine

### Model Training

Train all three models for a coin with:

```bash
python -m ml_engine.train_model bitcoin
```

Or from Python:

```python
from ml_engine.train_model import train_all_models

results = train_all_models('bitcoin')
# [
#   {'model_name': 'random_forest', 'rmse': 312.4, 'mae': 198.2, 'r2': 0.9871, 'directional_accuracy': 0.73},
#   {'model_name': 'xgboost',       'rmse': 289.1, 'mae': 175.6, 'r2': 0.9903, 'directional_accuracy': 0.76},
#   {'model_name': 'lstm',          'rmse': 401.2}
# ]
```

### RandomForest (`ml_engine/train_model.py`)

- **Algorithm:** scikit-learn `RandomForestRegressor`
- **Hyperparameters:** 100 estimators, max depth 5, all CPU cores (`n_jobs=-1`)
- **Train/test split:** Chronological — last 20% of rows used for testing (no shuffle to prevent data leakage)
- **Confidence estimation:** Inter-tree prediction variance. Coefficient of variation = `std / mean`. Confidence = `1 - CV`, clipped to `[0, 1]`

### XGBoost (`ml_engine/train_model.py`)

- **Algorithm:** `xgboost.XGBRegressor`
- **Hyperparameters:** 100 estimators, learning rate 0.1, max depth 4, early stopping on validation loss
- **Train/test split:** Same chronological approach as RandomForest
- **Confidence:** Fixed at 0.70 placeholder (suitable for calibration via conformal prediction in future)

### LSTM (`ml_engine/train_model.py`)

- **Architecture:** `LSTM(32) → Dropout(0.1) → Dense(16, relu) → Dense(1)`
- **Input:** Sequence of raw scaled prices (not engineered features) over a look-back window
- **Look-back window:** Adaptive — `min(30, len(data) // 3)`. Ensures LSTM works even on sparse data
- **Scaling:** `MinMaxScaler` fitted on training data only — scaler is saved alongside the model to prevent data leakage during inference
- **Training:** Up to 50 epochs, `EarlyStopping(patience=5)`, batch size adapts to data size
- **Saved files:** `lstm_model/` (Keras SavedModel), `lstm_scaler.joblib`, `lstm_look_back.joblib`

### Evaluation Metrics (`ml_engine/evaluate_model.py`)

| Metric | Description |
|---|---|
| RMSE | Root Mean Square Error — penalises large price deviations |
| MAE | Mean Absolute Error — average absolute dollar error |
| R² | Coefficient of determination — 1.0 = perfect fit |
| Directional Accuracy | % of timesteps where model correctly predicted up/down direction |

---

## Prediction Service

`prediction_service/predictor.py` loads a trained model and generates a next-interval forecast.

```python
from prediction_service.predictor import predict_price, save_prediction

result = predict_price('bitcoin', model_name='xgboost')

print(result.to_dict())
# {
#   "coin": "bitcoin",
#   "model_name": "xgboost",
#   "predicted_price": 84321.50,
#   "current_price": 83750.00,
#   "confidence": 0.7842,
#   "trend": "bullish",
#   "prediction_time": "2025-03-15T10:00:00",
#   "target_time": "2025-03-15T10:05:00"
# }

save_prediction(result)   # persists to model_predictions table
```

**Trend classification:**

| Condition | Trend |
|---|---|
| `(predicted - current) / current > 0.005` | `bullish` |
| `(predicted - current) / current < -0.005` | `bearish` |
| Otherwise | `neutral` |

The 0.5% threshold avoids noisy micro-movements being labelled as directional signals.

---

## RAG Insight Engine

The insight engine explains *why* a price is moving using a Retrieval-Augmented Generation pipeline.

### Pipeline Steps

```
1. News scraping  →  2. DB storage  →  3. Embedding  →  4. FAISS index  →  5. Retrieval  →  6. GPT synthesis
```

### `insight_engine/news_scraper.py`

Fetches articles from the **CoinDesk RSS feed** and filters by coin-specific keywords:

| Coin | Keywords |
|---|---|
| bitcoin | `bitcoin`, `btc` |
| ethereum | `ethereum`, `eth` |
| solana | `solana`, `sol` |
| binancecoin | `binance`, `bnb` |
| ripple | `ripple`, `xrp` |

Only articles where either the headline or summary contains a matching keyword are stored. This keeps the FAISS index focused and improves retrieval precision.

### `insight_engine/embeddings.py`

Converts stored news articles into OpenAI embeddings (`text-embedding-3-small`) and stores them in a **FAISS flat index** on disk at `data/faiss_index/{coin}/`.

- **Build from scratch:** `build_vector_store(coin)` — loads last 7 days from DB, embeds, saves
- **Incremental update:** `add_articles_to_store(coin, new_docs)` — appends new articles to existing index
- **Load existing:** `load_vector_store(coin)` — returns the saved FAISS index or `None` if not built yet

### `insight_engine/rag_pipeline.py`

Uses a **LangChain LCEL chain** (not the deprecated `RetrievalQA`):

```python
chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | ChatOpenAI(model="gpt-4o-mini")
    | StrOutputParser()
)
```

Retrieves the top-5 most relevant articles by semantic similarity, then asks GPT-4o-mini to synthesise a 2–3 sentence explanation referencing specific events.

**Example output:**
```
Bitcoin is showing bullish momentum driven by renewed institutional buying
and positive ETF inflow data. Regulatory clarity signals from the US SEC
have boosted market sentiment, while on-chain metrics indicate reduced
selling pressure from long-term holders.
```

**Fallback behaviour:** If `OPENAI_API_KEY` is not set, a plain summary is returned showing current price, predicted price, and trend label — no API calls are made.

---

## Visualization Layer

`visualization/chart_generator.py` returns JSON payloads ready for any charting library (Recharts, Chart.js, Plotly, etc.).

```python
from visualization.chart_generator import (
    generate_price_chart_data,
    generate_heatmap_data,
    generate_market_share_data,
    generate_volume_spike_data,
)

# Price chart with SMA overlays and prediction markers
data = generate_price_chart_data('bitcoin', days=30)
# Returns: { labels, price, sma_7, sma_30, rsi, macd, predicted }

# 7-day change heatmap for all coins
data = generate_heatmap_data(days=7)
# Returns: { coins, change_pct_7d, heatmap }

# Market cap dominance
data = generate_market_share_data()
# Returns: { labels, market_caps, dominance_pct }

# Volume spike events
data = generate_volume_spike_data('bitcoin', days=14)
# Returns: { timestamps, volume, volume_zscore, spikes }
```

---

## API Reference

Start the server:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI: `http://localhost:8000/docs`
ReDoc: `http://localhost:8000/redoc`

### Endpoints

#### `GET /live-data/{coin}`

Fetches the latest live market data for a single coin.

```bash
curl http://localhost:8000/live-data/bitcoin
```

```json
{
  "status": "success",
  "data": {
    "coin": "bitcoin",
    "timestamp": "2025-03-15T10:00:00",
    "price": 84231.50,
    "volume": 52000000000,
    "market_cap": 1660000000000,
    "circulating_supply": 19700000,
    "change_percentage_24h": 1.45,
    "change_percentage_7d": 3.20
  }
}
```

#### `GET /live-data`

Returns live data for all supported coins.

#### `GET /prediction/{coin}?model=xgboost`

Generates a next-interval price prediction.

**Query parameters:**

| Parameter | Values | Default |
|---|---|---|
| `model` | `xgboost`, `random_forest`, `lstm` | `xgboost` |

```bash
curl "http://localhost:8000/prediction/bitcoin?model=xgboost"
```

```json
{
  "status": "success",
  "data": {
    "coin": "bitcoin",
    "model_name": "xgboost",
    "predicted_price": 84750.00,
    "current_price": 84231.50,
    "confidence": 0.78,
    "trend": "bullish",
    "prediction_time": "2025-03-15T10:00:00",
    "target_time": "2025-03-15T10:05:00"
  }
}
```

**Error (model not trained):** Returns HTTP 404 with instructions to run training.

#### `GET /insights/{coin}`

Returns an AI-generated explanation of why the coin price is moving.

```bash
curl http://localhost:8000/insights/bitcoin
```

```json
{
  "status": "success",
  "coin": "bitcoin",
  "trend": "bullish",
  "current_price": 84231.50,
  "predicted_price": 84750.00,
  "insight": "Bitcoin is showing bullish momentum driven by renewed institutional buying..."
}
```

#### `GET /visualizations/{coin}?days=30`

Returns chart data bundles for a coin.

**Query parameters:**

| Parameter | Range | Default |
|---|---|---|
| `days` | 1–365 | 30 |

Returns price line with SMA overlays, RSI, MACD, prediction markers, and volume spike data.

#### `GET /visualizations/market/heatmap?days=7`

Returns 7-day percentage change data for all coins — suitable for a color-coded heatmap.

#### `GET /visualizations/market/dominance`

Returns current market-cap dominance percentages — suitable for a pie/donut chart.

---

## Scheduler & Automation

`run_pipeline.py` uses `APScheduler` with a `BackgroundScheduler` (UTC timezone) to automate the entire system.

```python
# Job 1 — runs every DATA_REFRESH_INTERVAL_MINUTES (default: 5)
job_fetch_and_store()
# → fetch_live_data() → save_market_data() → fetch_news() → save_news()

# Job 2 — runs every MODEL_RETRAIN_INTERVAL_HOURS (default: 1)
job_retrain_models()
# → train_all_models(coin) for each supported coin

# Job 3 — runs every 1 hour (aligned with retraining)
job_rebuild_embeddings()
# → build_vector_store(coin) for each supported coin
```

Each job has `max_instances=1` to prevent overlap if a job takes longer than its interval.

---

## Running the System

### Recommended workflow (3 terminals)

**Terminal 1 — Seed history and start the pipeline**

```bash
# First time only
python seed_historical_data.py

# Start the live pipeline (keep running permanently)
python run_pipeline.py
```

**Terminal 2 — Train models** (after pipeline has run at least once)

```bash
python -m ml_engine.train_model bitcoin
python -m ml_engine.train_model ethereum
python -m ml_engine.train_model solana
python -m ml_engine.train_model binancecoin
python -m ml_engine.train_model ripple
```

**Terminal 3 — Start the API server**

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Data flow dependencies

```
seed_historical_data.py     ← run once
        ↓
run_pipeline.py             ← must be running (populates DB)
        ↓
python -m ml_engine.train_model bitcoin   ← needs DB rows
        ↓
uvicorn api.main:app        ← needs trained models for /prediction
```

---

## Supported Coins

Default coins (configurable via `.env`):

| Coin | CoinGecko Slug | Binance Symbol |
|---|---|---|
| Bitcoin | `bitcoin` | BTCUSDT |
| Ethereum | `ethereum` | ETHUSDT |
| Solana | `solana` | SOLUSDT |
| BNB | `binancecoin` | BNBUSDT |
| XRP | `ripple` | XRPUSDT |

**Adding more coins:** Edit `SUPPORTED_COINS_RAW` in `.env`. Use the exact CoinGecko slug found in the URL at `coingecko.com/en/coins/{slug}`.

```env
SUPPORTED_COINS_RAW=bitcoin,ethereum,solana,binancecoin,ripple,cardano,dogecoin,polkadot
```

> CoinGecko free tier supports ~30 API calls/minute. For more than 8–10 coins, increase `DATA_REFRESH_INTERVAL_MINUTES` to 10 or register for a free API key.

---

## Troubleshooting

**`error parsing value for field "supported_coins"`**
The `SUPPORTED_COINS` variable was renamed. Ensure your `.env` uses `SUPPORTED_COINS_RAW` (not `SUPPORTED_COINS`).

**`connection to server at "localhost" port 5432 failed`**
Your `DATABASE_URL` points to PostgreSQL but PostgreSQL is not running. Switch to SQLite for local development:
```env
DATABASE_URL=sqlite:///./data/crypto.db
```

**`No module named 'langchain.chains'`**
LangChain v0.2+ split its packages. Ensure you are using `langchain-core` and `langchain-community`:
```bash
pip install langchain-core langchain-community langchain-openai
```

**`RetryError: HTTPError` on data fetch**
CoinGecko is rate-limiting your IP. The system will automatically fall back to `/simple/price`. If the error persists, increase `DATA_REFRESH_INTERVAL_MINUTES` to 10 or add a `COINGECKO_API_KEY`.

**`No data available for bitcoin` during training**
The pipeline has not collected enough data yet. Run `seed_historical_data.py` to backfill 365 days instantly, then retrain.

**`No trained model found` from `/prediction` endpoint**
Models must be trained before predictions are available. Run:
```bash
python -m ml_engine.train_model bitcoin
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes with descriptive messages
4. Open a pull request describing what you changed and why

Please ensure new modules include type hints, docstrings, and loguru logging consistent with the existing codebase.

---

## License

MIT License — see `LICENSE` for details.

---

*Built with Python 3.12 · FastAPI · scikit-learn · XGBoost · TensorFlow · LangChain · FAISS*
