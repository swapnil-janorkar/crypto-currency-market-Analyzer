"""
database/db_connector.py
------------------------
Provides the SQLAlchemy engine, session factory, and all ORM models.

Tables
------
- crypto_market_data  : raw OHLCV + metadata fetched every N minutes
- model_predictions   : model outputs (price, confidence, trend)
- news_data           : scraped headlines for RAG context
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Generator

from loguru import logger
from sqlalchemy import (
    Column, DateTime, Enum, Float, Integer,
    String, Text, create_engine, Index,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from config import settings


# ── Engine & Session ──────────────────────────────────────────────────────────

engine = create_engine(
    settings.database_url,
    # SQLite needs this; harmless for Postgres
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ── Base ──────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── ORM Models ────────────────────────────────────────────────────────────────

class CryptoMarketData(Base):
    """One row per (coin, timestamp) snapshot fetched from the live pipeline."""

    __tablename__ = "crypto_market_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    coin = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    price = Column(Float, nullable=False)
    volume = Column(Float)
    market_cap = Column(Float)
    circulating_supply = Column(Float)
    change_percentage_24h = Column(Float)
    change_percentage_7d = Column(Float)

    __table_args__ = (
        Index("ix_coin_ts", "coin", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<CryptoMarketData coin={self.coin} price={self.price} ts={self.timestamp}>"


class TrendEnum(str, enum.Enum):
    bullish = "bullish"
    bearish = "bearish"
    neutral = "neutral"


class ModelPrediction(Base):
    """Stores model outputs so we can track accuracy over time."""

    __tablename__ = "model_predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    coin = Column(String(50), nullable=False, index=True)
    model_name = Column(String(50), nullable=False)
    predicted_price = Column(Float, nullable=False)
    confidence = Column(Float)                      # 0–1 range
    trend = Column(Enum(TrendEnum), nullable=False)
    prediction_time = Column(DateTime, default=datetime.utcnow)
    target_time = Column(DateTime)                  # when prediction is for

    def __repr__(self) -> str:
        return (
            f"<ModelPrediction coin={self.coin} "
            f"price={self.predicted_price:.2f} trend={self.trend}>"
        )


class NewsData(Base):
    """Raw headlines ingested for the RAG pipeline."""

    __tablename__ = "news_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    coin = Column(String(50), nullable=False, index=True)
    headline = Column(Text, nullable=False)
    summary = Column(Text)
    source = Column(String(200))
    url = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<NewsData coin={self.coin} source={self.source}>"


class User(Base):
    """Local demo user accounts for dashboard authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<User username={self.username}>"


# ── Helpers ───────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables (idempotent — safe to call on every startup)."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialised.")


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a DB session and ensures it is closed.

    Usage
    -----
    >>> @app.get("/example")
    ... def endpoint(db: Session = Depends(get_db)):
    ...     ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
