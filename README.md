# CryptoPredictor — Production ML Platform

A production-ready cryptocurrency prediction system converted from your Jupyter
notebook. It fetches live prices, engineers features, trains three model types,
explains price moves with RAG, and exposes everything through a FastAPI layer.

---

## Project Structure

```
crypto_predictor/
├── data_pipeline/
│   ├── fetch_data.py          # CoinGecko + Binance live data
│   ├── preprocess.py          # Clean & deduplicate raw rows
│   └── feature_engineering.py # SMA, RSI, MACD, volume spikes, lags
│
├── ml_engine/
│   ├── train_model.py         # RandomForest, XGBoost, LSTM trainers
│   ├── evaluate_model.py      # RMSE, MAE, R², directional accuracy
│   └── save_model.py          # joblib + Keras SavedModel helpers
│
├── prediction_service/
│   └── predictor.py           # load model → predict → trend + confidence
│
├── insight_engine/
│   ├── news_scraper.py        # CoinDesk RSS + CryptoPanic
│   ├── embeddings.py          # OpenAI embeddings → FAISS index
│   └── rag_pipeline.py        # LangChain RetrievalQA → GPT insight
│
├── visualization/
│   └── chart_generator.py     # JSON payloads for frontend charts
│
├── database/
│   └── db_connector.py        # SQLAlchemy ORM (SQLite / PostgreSQL)
│
├── api/
│   └── main.py                # FastAPI server (8 endpoints)
│
├── models/                    # Saved model files (auto-created)
├── data/                      # SQLite DB + FAISS indexes
├── config.py                  # Pydantic settings (reads .env)
├── run_pipeline.py            # APScheduler — data + retraining jobs
└── requirements.txt
```

---

## Quick Start

### 1. Clone & install dependencies

```bash
cd crypto_predictor
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY for RAG insights
# Leave DATABASE_URL as SQLite for local dev (no setup needed)
```

### 3. Start the live data pipeline (terminal 1)

```bash
python run_pipeline.py
```

This will:
- Initialise the database
- Immediately fetch live prices for bitcoin, ethereum, solana, binancecoin, ripple
- Schedule refreshes every 5 minutes
- Schedule model retraining every hour

### 4. Train models manually (optional — first run)

```bash
# Train all three models for Bitcoin
python -m ml_engine.train_model bitcoin

# Or from Python:
from ml_engine.train_model import train_all_models
results = train_all_models("bitcoin")
# [{'model_name': 'random_forest', 'rmse': 312.4, 'r2': 0.9871, ...},
#  {'model_name': 'xgboost',       'rmse': 289.1, 'r2': 0.9903, ...},
#  {'model_name': 'lstm',          'rmse': 401.2}]
```

### 5. Start the API server (terminal 2)

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI → http://localhost:8000/docs

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/live-data/{coin}` | Latest price, volume, market cap |
| GET | `/live-data` | All supported coins |
| GET | `/prediction/{coin}?model=xgboost` | ML price prediction |
| GET | `/insights/{coin}` | RAG-powered market explanation |
| GET | `/visualizations/{coin}?days=30` | Chart data (price, RSI, MACD, volume) |
| GET | `/visualizations/market/heatmap` | 7-day change heatmap |
| GET | `/visualizations/market/dominance` | Market cap pie data |

### Example — Get a prediction

```bash
curl http://localhost:8000/prediction/bitcoin?model=xgboost
```

```json
{
  "status": "success",
  "data": {
    "coin": "bitcoin",
    "model_name": "xgboost",
    "predicted_price": 68124.33,
    "current_price": 67500.00,
    "confidence": 0.7842,
    "trend": "bullish",
    "prediction_time": "2025-03-15T10:00:00",
    "target_time": "2025-03-15T10:05:00"
  }
}
```

### Example — Get RAG insight

```bash
curl http://localhost:8000/insights/bitcoin
```

```json
{
  "status": "success",
  "coin": "bitcoin",
  "trend": "bullish",
  "current_price": 67500.0,
  "predicted_price": 68124.33,
  "insight": "Bitcoin is showing bullish momentum driven by renewed institutional buying and positive ETF inflow data. Regulatory clarity signals from the US SEC have boosted market sentiment, while on-chain metrics indicate reduced selling pressure from long-term holders."
}
```

---

## Supported Coins (default)

`bitcoin`, `ethereum`, `solana`, `binancecoin`, `ripple`

Add more in `.env`:
```
SUPPORTED_COINS=bitcoin,ethereum,solana,cardano,dogecoin
```

---

## Switching to PostgreSQL

```env
DATABASE_URL=postgresql://user:password@localhost:5432/crypto_predictor
```

Then run `python -c "from database.db_connector import init_db; init_db()"`.

---

## Features Computed

| Feature | Description |
|---------|-------------|
| `sma_7/14/30` | Simple moving averages |
| `rsi_14` | Relative Strength Index |
| `macd / macd_signal` | MACD line + signal |
| `volatility_14d` | 14-day rolling return std |
| `momentum_1d/7d` | Percentage price change |
| `volume_zscore` | Volume z-score (spike detection) |
| `price_lag_1/3/7` | Lagged price values |
