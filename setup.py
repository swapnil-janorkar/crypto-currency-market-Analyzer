"""
setup.py
--------
Run once after installing requirements to bootstrap the system:

    python setup.py

What it does
------------
1. Creates .env from .env.example (if missing)
2. Creates the database schema
3. Runs an initial live data fetch
4. Prints next steps
"""

import os
import sys
import shutil


def main():
    print("\n=== CryptoPredictor Setup ===\n")

    # 1. .env
    if not os.path.exists(".env"):
        shutil.copy(".env.example", ".env")
        print("✅  Created .env from .env.example")
        print("    ➜  Open .env and add your OPENAI_API_KEY if you want RAG insights.\n")
    else:
        print("✅  .env already exists — skipping.\n")

    # 2. Directories
    for d in ["models", "data", "logs", "data/faiss_index"]:
        os.makedirs(d, exist_ok=True)
    print("✅  Created output directories (models/, data/, logs/).\n")

    # 3. Database
    print("🗄️  Initialising database …")
    from database.db_connector import init_db
    init_db()
    print("✅  Database schema ready.\n")

    # 4. First data fetch
    print("📡  Running initial live data fetch …")
    try:
        from data_pipeline.fetch_data import fetch_live_data, save_market_data
        from config import settings
        rows = fetch_live_data(settings.supported_coins)
        save_market_data(rows)
        print(f"✅  Fetched and stored {len(rows)} coins.\n")
    except Exception as exc:
        print(f"⚠️   Live fetch failed (you can retry later): {exc}\n")

    # 5. Next steps
    print("=" * 50)
    print("Next steps:")
    print()
    print("  1. Train models (needs ~90 days of data after running pipeline a while):")
    print("     python -m ml_engine.train_model bitcoin")
    print()
    print("  2. Start the live data pipeline (terminal 1):")
    print("     python run_pipeline.py")
    print()
    print("  3. Start the API server (terminal 2):")
    print("     uvicorn api.main:app --reload --port 8000")
    print()
    print("  4. Open Swagger UI:")
    print("     http://localhost:8000/docs")
    print()
    print("  Or in VS Code: open crypto_predictor.code-workspace")
    print("  and use the Run & Debug panel (F5) to launch any component.")
    print()


if __name__ == "__main__":
    main()
