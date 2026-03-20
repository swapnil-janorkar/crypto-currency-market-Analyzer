"""
insight_engine/embeddings.py
-----------------------------
Creates OpenAI embeddings for news articles and stores them in FAISS.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from loguru import logger
from sqlalchemy import select

from config import settings
from database.db_connector import NewsData, SessionLocal


def _get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        openai_api_key=settings.openai_api_key,
        model="text-embedding-3-small",
    )


def _coin_index_path(coin: str) -> str:
    return os.path.join(settings.faiss_index_path, coin)


def _load_recent_news(coin: str, days: int = 7) -> list[Document]:
    cutoff = datetime.utcnow() - timedelta(days=days)
    db = SessionLocal()
    try:
        stmt = (
            select(NewsData)
            .where(NewsData.coin == coin, NewsData.timestamp >= cutoff)
            .order_by(NewsData.timestamp.desc())
        )
        rows = db.execute(stmt).scalars().all()
    finally:
        db.close()

    return [
        Document(
            page_content=f"{r.headline}. {r.summary or ''}".strip(),
            metadata={
                "source": r.source or "",
                "url": r.url or "",
                "timestamp": r.timestamp.isoformat() if r.timestamp else "",
                "coin": coin,
            },
        )
        for r in rows
        if r.headline
    ]


def build_vector_store(coin: str) -> FAISS:
    """Build (or rebuild) the FAISS index for a coin from recent DB news."""
    docs = _load_recent_news(coin)
    if not docs:
        raise ValueError(f"No news articles found for {coin} to embed.")

    logger.info(f"Embedding {len(docs)} articles for {coin} ...")
    embeddings = _get_embeddings()
    store = FAISS.from_documents(docs, embeddings)

    index_path = _coin_index_path(coin)
    os.makedirs(index_path, exist_ok=True)
    store.save_local(index_path)
    logger.success(f"FAISS index saved -> {index_path}")
    return store


def load_vector_store(coin: str) -> FAISS | None:
    """Load an existing FAISS index from disk. Returns None if not built yet."""
    index_path = _coin_index_path(coin)
    if not os.path.exists(index_path):
        return None
    embeddings = _get_embeddings()
    return FAISS.load_local(
        index_path, embeddings, allow_dangerous_deserialization=True
    )


def add_articles_to_store(coin: str, new_docs: list[Document]) -> FAISS:
    """Incrementally add new documents to an existing FAISS index."""
    store = load_vector_store(coin)
    embeddings = _get_embeddings()
    if store is None:
        store = FAISS.from_documents(new_docs, embeddings)
    else:
        store.add_documents(new_docs)
    store.save_local(_coin_index_path(coin))
    return store