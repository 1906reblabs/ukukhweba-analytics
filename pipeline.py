#!/usr/bin/env python3
"""
JSE Sentiment Engine — Daily Pipeline
======================================
Run daily via GitHub Actions (free) at 18:00 SAST (after JSE close).

Usage:
    python -m sentiment_engine.pipeline
    python -m sentiment_engine.pipeline --date 2025-03-15  # backfill
    python -m sentiment_engine.pipeline --dry-run          # no DB writes
"""

import argparse
import logging
import sys
from datetime import datetime

from .scrapers.moneyweb import MoneywebScraper
from .scrapers.businesslive import BusinessLiveScraper
from .scrapers.sens import SENSScraper
from .nlp.scorer import score_all, aggregate_ticker_sentiment
from .storage.supabase_client import upsert_articles, upsert_ticker_sentiment

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("pipeline")


def run_pipeline(date_str: str = None, dry_run: bool = False) -> dict:
    """
    Full pipeline: scrape → score → store.
    Returns summary dict for monitoring.
    """
    if not date_str:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

    logger.info(f"═══ JSE Sentiment Pipeline — {date_str} ═══")
    summary = {
        "date": date_str,
        "articles_scraped": 0,
        "articles_stored": 0,
        "tickers_scored": 0,
        "top_bullish": [],
        "top_bearish": [],
        "errors": [],
    }

    # ── Step 1: Scrape ─────────────────────────────────────────
    all_articles = []

    scrapers = [
        ("Moneyweb",     MoneywebScraper()),
        ("BusinessLive", BusinessLiveScraper()),
        ("SENS",         SENSScraper()),
    ]

    for name, scraper in scrapers:
        try:
            logger.info(f"\n▶ Scraping {name}...")
            articles = scraper.fetch()
            all_articles.extend(articles)
            logger.info(f"  {name}: {len(articles)} articles")
        except Exception as e:
            msg = f"{name} scraper failed: {e}"
            logger.error(msg)
            summary["errors"].append(msg)

    summary["articles_scraped"] = len(all_articles)
    logger.info(f"\n✓ Total articles scraped: {len(all_articles)}")

    if not all_articles:
        logger.error("No articles fetched — check network and source sites")
        return summary

    # ── Step 2: Score ──────────────────────────────────────────
    logger.info("\n▶ Running sentiment scoring...")
    scored_articles = score_all(all_articles)

    # Filter: only store articles with at least one ticker match or strong signal
    relevant_articles = [
        a for a in scored_articles
        if a.matched_tickers or abs(a.sentiment_compound or 0) > 0.3
    ]
    logger.info(
        f"  Scored {len(scored_articles)} articles | "
        f"{len(relevant_articles)} relevant (ticker match or strong signal)"
    )

    # ── Step 3: Aggregate per ticker ───────────────────────────
    logger.info("\n▶ Aggregating ticker sentiment...")
    ticker_rows = aggregate_ticker_sentiment(scored_articles, date_str)
    summary["tickers_scored"] = len(ticker_rows)

    # Log top movers
    if ticker_rows:
        bullish = [r for r in ticker_rows if r["sentiment_mean"] > 0.05][:5]
        bearish = [r for r in reversed(ticker_rows) if r["sentiment_mean"] < -0.05][:5]

        summary["top_bullish"] = [(r["ticker"], r["sentiment_mean"]) for r in bullish]
        summary["top_bearish"] = [(r["ticker"], r["sentiment_mean"]) for r in bearish]

        logger.info(f"\n  📈 Most bullish tickers today:")
        for r in bullish:
            logger.info(
                f"     {r['ticker']:<12} score={r['sentiment_mean']:+.3f} "
                f"articles={r['article_count']}"
            )
        logger.info(f"\n  📉 Most bearish tickers today:")
        for r in bearish:
            logger.info(
                f"     {r['ticker']:<12} score={r['sentiment_mean']:+.3f} "
                f"articles={r['article_count']}"
            )

    # ── Step 4: Store ──────────────────────────────────────────
    if dry_run:
        logger.info("\n⚠ DRY RUN — skipping database writes")
        return summary

    logger.info("\n▶ Storing to Supabase...")
    summary["articles_stored"] = upsert_articles(relevant_articles, date_str)
    upsert_ticker_sentiment(ticker_rows)

    logger.info(f"\n═══ Pipeline complete ═══")
    logger.info(f"  Articles stored:  {summary['articles_stored']}")
    logger.info(f"  Tickers scored:   {summary['tickers_scored']}")
    logger.info(f"  Errors:           {len(summary['errors'])}")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JSE Sentiment Pipeline")
    parser.add_argument("--date", help="Date to run for (YYYY-MM-DD)", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Skip DB writes")
    args = parser.parse_args()

    result = run_pipeline(date_str=args.date, dry_run=args.dry_run)
    sys.exit(0 if not result["errors"] else 1)
