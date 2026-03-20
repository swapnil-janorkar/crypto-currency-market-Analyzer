"""
config.py
---------
Centralised configuration using pydantic-settings.
All values are loaded from environment variables or the .env file.
"""

from __future__ import annotations
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./data/crypto.db"

    # ── External APIs ─────────────────────────────────────────────────────────
    coingecko_api_key: str = ""
    binance_api_key: str = ""
    binance_secret_key: str = ""

    # ── OpenAI / RAG ──────────────────────────────────────────────────────────
    openai_api_key: str = ""

    # ── App Behaviour ─────────────────────────────────────────────────────────
    data_refresh_interval_minutes: int = 5
    model_retrain_interval_hours: int = 1
    log_level: str = "INFO"

    # Stored as a plain string so pydantic-settings never tries to JSON-parse it.
    # Use settings.supported_coins (the property below) everywhere in the code.
    supported_coins_raw: str = "bitcoin,ethereum,solana,binancecoin,ripple"

    # ── Paths ─────────────────────────────────────────────────────────────────
    models_dir: str = "models"
    data_dir: str = "data"
    faiss_index_path: str = "data/faiss_index"

    # ── Derived ───────────────────────────────────────────────────────────────
    # Populated by the validator below — never set this directly in .env
    supported_coins: List[str] = []

    @model_validator(mode="after")
    def _parse_coins(self) -> "Settings":
        """Split supported_coins_raw into a proper list."""
        raw = self.supported_coins_raw.strip()
        self.supported_coins = [c.strip() for c in raw.split(",") if c.strip()]
        return self


# Singleton — import this everywhere
settings = Settings()
