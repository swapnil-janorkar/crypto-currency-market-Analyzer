"""
insight_engine/rag_pipeline.py
-------------------------------
RAG pipeline that explains why a cryptocurrency price moved.
"""

from __future__ import annotations

from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from loguru import logger

from config import settings
from insight_engine.embeddings import build_vector_store, load_vector_store
from insight_engine.news_scraper import fetch_news, save_news


INSIGHT_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template="""
You are a senior cryptocurrency market analyst.

Use the following recent news articles to explain the price movement:
{context}

Question: {question}

Provide a concise 2-3 sentence insight that:
1. Explains the key reasons for the price movement
2. Mentions specific news events if available
3. Notes whether the trend is likely to continue

Answer:""",
)


def _ensure_vector_store(coin: str):
    store = load_vector_store(coin)
    if store is not None:
        return store
    logger.info(f"No FAISS index for {coin}. Scraping news ...")
    articles = fetch_news(coin, max_articles=30)
    if articles:
        save_news(articles)
    return build_vector_store(coin)


def generate_market_insight(
    coin: str,
    current_price: float,
    predicted_price: float,
    trend: str,
) -> str:
    """
    Generate a natural-language explanation of a coin's price movement.

    Returns a human-readable market insight string.
    Falls back to a plain summary if OpenAI key is not configured.
    """
    if not settings.openai_api_key:
        price_change_pct = (predicted_price - current_price) / current_price * 100
        arrow = "▲" if price_change_pct > 0 else "▼"
        return (
            f"{coin.capitalize()} is showing a {trend} signal. "
            f"Current: ${current_price:,.2f} | Predicted: ${predicted_price:,.2f} "
            f"({arrow} {abs(price_change_pct):.1f}%). "
            "(Set OPENAI_API_KEY in .env for AI-powered insights.)"
        )

    price_change_pct = (predicted_price - current_price) / current_price * 100
    direction = "rise" if price_change_pct > 0 else "fall"
    question = (
        f"Why might {coin} price {direction} by "
        f"{abs(price_change_pct):.1f}% from ${current_price:,.2f} "
        f"to ${predicted_price:,.2f}? The model indicates a {trend} trend."
    )

    try:
        store = _ensure_vector_store(coin)
        retriever = store.as_retriever(search_kwargs={"k": 5})
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            openai_api_key=settings.openai_api_key,
        )

        def format_docs(docs):
            return "\n\n".join(d.page_content for d in docs)

        chain = (
            {"context": retriever | format_docs, "question": RunnablePassthrough()}
            | INSIGHT_PROMPT
            | llm
            | StrOutputParser()
        )

        insight = chain.invoke(question)
        logger.success(f"Generated insight for {coin}.")
        return insight.strip()

    except Exception as exc:
        logger.error(f"RAG pipeline failed for {coin}: {exc}")
        price_change_pct = (predicted_price - current_price) / current_price * 100
        return (
            f"{coin.capitalize()} is showing a {trend} outlook. "
            f"Predicted: ${predicted_price:,.2f} "
            f"({'▲' if price_change_pct > 0 else '▼'} {abs(price_change_pct):.1f}%). "
            f"(AI insight unavailable: {exc})"
        )