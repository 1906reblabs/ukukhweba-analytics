from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from .ticker_mapper import map_article_to_tickers, get_load_shedding_stage
from ..scrapers.base import Article
import logging

logger = logging.getLogger(__name__)

# ── SA Financial Lexicon Booster ──────────────────────────────
# VADER was trained on English social media. We add SA-specific
# financial terms. Positive/negative scores: -4 to +4.
# This is your proprietary NLP edge. Expand it weekly.
SA_FINANCIAL_LEXICON = {
    # Load shedding — always negative for markets
    "load shedding": -3.0,
    "loadshedding": -3.0,
    "load-shedding": -3.0,
    "stage 6": -3.5,
    "stage 8": -4.0,
    "rolling blackouts": -2.5,
    "power outage": -2.0,
    "power cuts": -2.0,
    "eskom failure": -3.5,
    "eskom breakdown": -3.0,
    "diesel levy": -1.5,
    "generator costs": -1.5,

    # Positive SA terms
    "just energy transition": 1.5,
    "jet": 0.5,  # SA context: Just Energy Transition, not airline
    "renewable energy": 2.0,
    "solar capacity": 1.5,
    "stage 0": 2.5,
    "load shedding suspended": 3.0,
    "eskom recovery": 2.5,

    # Mining-specific
    "pgm prices": 0.5,
    "palladium": 0.5,
    "rhodium": 0.5,
    "mining royalties": -1.5,
    "mining strike": -3.0,
    "shaft closure": -3.5,
    "seismic event": -2.0,
    "deep level mining": 0.0,

    # SA macro
    "rand strengthens": 2.5,
    "rand weakens": -2.5,
    "rand collapse": -3.5,
    "rating downgrade": -3.5,
    "junk status": -4.0,
    "rating upgrade": 3.5,
    "sarb rate cut": 2.0,
    "sarb rate hike": -1.5,
    "current account surplus": 2.0,
    "current account deficit": -1.5,
    "state capture": -2.0,
    "cadre deployment": -1.5,
    "expropriation": -2.5,
    "expropriation without compensation": -3.5,

    # Corporate actions (positive signals)
    "share buyback": 2.5,
    "special dividend": 3.0,
    "dividend increase": 2.5,
    "earnings beat": 3.0,
    "upgraded guidance": 2.5,
    "record profit": 3.0,
    "record earnings": 3.0,
    "headline earnings growth": 2.5,
    "heps growth": 2.0,

    # Corporate actions (negative signals)
    "earnings miss": -3.0,
    "profit warning": -3.5,
    "cautionary announcement": -2.0,
    "rights issue": -1.5,  # dilutive
    "ceo resignation": -2.5,
    "ceo steps down": -2.0,
    "restatement": -3.0,
    "irregular expenditure": -2.5,
    "going concern": -4.0,
    "business rescue": -4.0,
    "provisional liquidation": -4.0,
    "trading halt": -2.0,

    # JSE-specific terms
    "sens announcement": 0.0,  # neutral, context matters
    "results announcement": 0.5,
    "interim results": 0.0,
    "final results": 0.0,
    "agm": 0.0,
}


def build_analyzer() -> SentimentIntensityAnalyzer:
    """Build VADER analyzer with SA financial lexicon injected."""
    analyzer = SentimentIntensityAnalyzer()
    # VADER allows you to update the lexicon — this is the power move
    analyzer.lexicon.update(SA_FINANCIAL_LEXICON)
    return analyzer


# Module-level analyzer — instantiate once, reuse across all articles
_ANALYZER = build_analyzer()


def score_article(article: Article) -> Article:
    """
    Score a single article. Mutates and returns the article.
    
    Scoring logic:
    - Title gets 2x weight (more signal per character in financial news)
    - SENS announcements get extra negative weighting on keywords
    - Load shedding stage extracted as separate signal
    """
    text = article.scoring_text()

    scores = _ANALYZER.polarity_scores(text)

    article.sentiment_compound = round(scores["compound"], 4)
    article.sentiment_positive = round(scores["pos"], 4)
    article.sentiment_negative = round(scores["neg"], 4)
    article.sentiment_neutral  = round(scores["neu"], 4)

    # Map to tickers
    article.matched_tickers = map_article_to_tickers(
        article.title,
        article.summary + " " + article.full_text
    )

    # Load shedding stage extraction
    stage = get_load_shedding_stage(article.title + " " + article.summary)
    if stage:
        # Store in full_text as metadata for now
        # Later: dedicated column in Supabase
        article.full_text = f"[LOAD_SHEDDING_STAGE:{stage}] " + article.full_text

    logger.debug(
        f"Scored: '{article.title[:50]}...' → "
        f"compound={article.sentiment_compound}, "
        f"tickers={article.matched_tickers}"
    )

    return article


def score_all(articles: list[Article]) -> list[Article]:
    """Score all articles in batch."""
    scored = []
    for article in articles:
        try:
            scored.append(score_article(article))
        except Exception as e:
            logger.error(f"Scoring failed for '{article.title[:40]}': {e}")
    return scored


def aggregate_ticker_sentiment(
    articles: list[Article],
    date_str: str,
) -> list[dict]:
    """
    The key output: one row per (ticker, date) with aggregated
    sentiment from all articles that mentioned that ticker.
    This is what gets stored in Supabase and queried for signals.
    """
    from collections import defaultdict
    import statistics

    ticker_articles = defaultdict(list)
    for article in articles:
        for ticker in article.matched_tickers:
            ticker_articles[ticker].append(article)

    rows = []
    for ticker, arts in ticker_articles.items():
        compounds = [a.sentiment_compound for a in arts if a.sentiment_compound is not None]
        if not compounds:
            continue

        rows.append({
            "ticker": ticker,
            "date": date_str,
            "sentiment_mean": round(statistics.mean(compounds), 4),
            "sentiment_median": round(statistics.median(compounds), 4),
            "sentiment_std": round(statistics.stdev(compounds), 4) if len(compounds) > 1 else 0.0,
            "article_count": len(arts),
            "positive_count": sum(1 for c in compounds if c > 0.05),
            "negative_count": sum(1 for c in compounds if c < -0.05),
            "neutral_count": sum(1 for c in compounds if -0.05 <= c <= 0.05),
            # Weighted sentiment: more articles = stronger signal
            "weighted_sentiment": round(
                sum(c * (1 + 0.1 * i) for i, c in enumerate(sorted(abs(c) for c in compounds)))
                / len(compounds),
                4
            ),
            "sources": list({a.source for a in arts}),
            "sample_headlines": [a.title[:100] for a in arts[:3]],
        })

    return sorted(rows, key=lambda x: abs(x["sentiment_mean"]), reverse=True)
