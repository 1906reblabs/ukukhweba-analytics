import os
import logging
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Supabase Table DDL ─────────────────────────────────────────
# Run this ONCE in your Supabase SQL editor before first run:
#
# CREATE TABLE IF NOT EXISTS jse_articles (
#     id               BIGSERIAL PRIMARY KEY,
#     source           TEXT NOT NULL,
#     title            TEXT NOT NULL,
#     url              TEXT UNIQUE,
#     published_at     TIMESTAMPTZ,
#     fetched_at       TIMESTAMPTZ DEFAULT NOW(),
#     summary          TEXT,
#     full_text        TEXT,
#     sentiment_compound   FLOAT,
#     sentiment_positive   FLOAT,
#     sentiment_negative   FLOAT,
#     sentiment_neutral    FLOAT,
#     matched_tickers  TEXT[],
#     date             DATE
# );
#
# CREATE TABLE IF NOT EXISTS jse_ticker_sentiment (
#     id                  BIGSERIAL PRIMARY KEY,
#     ticker              TEXT NOT NULL,
#     date                DATE NOT NULL,
#     sentiment_mean      FLOAT,
#     sentiment_median    FLOAT,
#     sentiment_std       FLOAT,
#     article_count       INTEGER,
#     positive_count      INTEGER,
#     negative_count      INTEGER,
#     neutral_count       INTEGER,
#     weighted_sentiment  FLOAT,
#     sources             TEXT[],
#     sample_headlines    TEXT[],
#     created_at          TIMESTAMPTZ DEFAULT NOW(),
#     UNIQUE(ticker, date)
# );
#
# CREATE INDEX idx_ticker_date ON jse_ticker_sentiment(ticker, date);
# CREATE INDEX idx_articles_date ON jse_articles(date);
# CREATE INDEX idx_articles_ticker ON jse_articles USING GIN(matched_tickers);
#
# -- Enable Row Level Security (free Supabase tier best practice)
# ALTER TABLE jse_articles ENABLE ROW LEVEL SECURITY;
# ALTER TABLE jse_ticker_sentiment ENABLE ROW LEVEL SECURITY;
# ────────────────────────────────────────────────────────────────


def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise EnvironmentError(
            "SUPABASE_URL and SUPABASE_KEY must be set. "
            "Copy .env.example to .env and fill in your values."
        )
    return create_client(url, key)


def upsert_articles(articles: list, date_str: str) -> int:
    """
    Insert articles, skipping duplicates (by URL).
    Returns count of new articles stored.
    """
    from ..scrapers.base import Article
    client = get_client()

    records = []
    for a in articles:
        if not isinstance(a, Article):
            continue
        records.append({
            "source": a.source,
            "title": a.title,
            "url": a.url or f"no-url-{hash(a.title)}",
            "published_at": a.published_at.isoformat() if a.published_at else None,
            "fetched_at": a.fetched_at.isoformat(),
            "summary": a.summary[:1000] if a.summary else "",
            "full_text": a.full_text[:3000] if a.full_text else "",
            "sentiment_compound": a.sentiment_compound,
            "sentiment_positive": a.sentiment_positive,
            "sentiment_negative": a.sentiment_negative,
            "sentiment_neutral": a.sentiment_neutral,
            "matched_tickers": a.matched_tickers,
            "date": date_str,
        })

    if not records:
        logger.warning("No records to insert")
        return 0

    # Upsert in batches of 100 (Supabase free tier limit)
    inserted = 0
    for i in range(0, len(records), 100):
        batch = records[i:i+100]
        try:
            result = (
                client.table("jse_articles")
                .upsert(batch, on_conflict="url")
                .execute()
            )
            inserted += len(batch)
            logger.info(f"Stored batch {i//100 + 1}: {len(batch)} articles")
        except Exception as e:
            logger.error(f"Batch insert failed: {e}")

    return inserted


def upsert_ticker_sentiment(rows: list[dict]) -> int:
    """
    Store daily ticker sentiment aggregates.
    This is the core time-series that becomes your signal moat.
    Uses UPSERT so re-running the pipeline on the same day is safe.
    """
    client = get_client()

    if not rows:
        return 0

    # Serialise list fields for Postgres
    serialised = []
    for row in rows:
        serialised.append({
            **row,
            "sources": row.get("sources", []),
            "sample_headlines": row.get("sample_headlines", []),
        })

    try:
        result = (
            client.table("jse_ticker_sentiment")
            .upsert(serialised, on_conflict="ticker,date")
            .execute()
        )
        logger.info(f"Upserted {len(serialised)} ticker sentiment rows")
        return len(serialised)
    except Exception as e:
        logger.error(f"Ticker sentiment upsert failed: {e}")
        return 0


def get_ticker_sentiment_history(
    ticker: str,
    days: int = 30
) -> list[dict]:
    """
    Query historical sentiment for a ticker — used in the Streamlit dashboard.
    Returns list of {date, sentiment_mean, article_count} dicts.
    """
    client = get_client()
    from datetime import timedelta

    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

    result = (
        client.table("jse_ticker_sentiment")
        .select("date, sentiment_mean, sentiment_median, article_count, sample_headlines")
        .eq("ticker", ticker)
        .gte("date", since)
        .order("date", desc=False)
        .execute()
    )

    return result.data or []


def get_top_movers_by_sentiment(date_str: str, limit: int = 10) -> dict:
    """
    Get the most bullish and bearish tickers by sentiment for a given date.
    This powers your 'Sentiment Movers' dashboard section.
    """
    client = get_client()

    result = (
        client.table("jse_ticker_sentiment")
        .select("*")
        .eq("date", date_str)
        .order("sentiment_mean", desc=True)
        .execute()
    )

    rows = result.data or []
    return {
        "most_bullish": rows[:limit],
        "most_bearish": rows[-limit:][::-1],
        "date": date_str,
        "total_tickers": len(rows),
    }
