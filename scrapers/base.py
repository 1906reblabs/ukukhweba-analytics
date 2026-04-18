from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

@dataclass
class Article:
    """Normalised article across all SA sources."""
    source: str
    title: str
    url: str
    published_at: datetime
    summary: str = ""
    full_text: str = ""
    author: str = ""
    # Populated after NLP pass
    sentiment_compound: Optional[float] = None
    sentiment_positive: Optional[float] = None
    sentiment_negative: Optional[float] = None
    sentiment_neutral: Optional[float] = None
    matched_tickers: list = field(default_factory=list)
    fetched_at: datetime = field(default_factory=datetime.utcnow)

    def scoring_text(self) -> str:
        """Text to run sentiment analysis on — title weighted heavily."""
        # Title carries more signal than body for market sentiment
        # Repeat title 2x to weight it without complex models
        return f"{self.title}. {self.title}. {self.summary} {self.full_text[:500]}"


class BaseScraper(ABC):
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; JSE-Intelligence-Bot/1.0; "
            "+https://github.com/YOUR_GITHUB/jse-intelligence)"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    REQUEST_TIMEOUT = 15
    RATE_LIMIT_SECONDS = 2  # be a good citizen

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def fetch(self) -> list[Article]:
        """Fetch and return normalised articles."""
        ...

    def _safe_date(self, date_str: str) -> datetime:
        """Parse various date formats from SA news sites."""
        import dateutil.parser
        try:
            return dateutil.parser.parse(date_str)
        except Exception:
            return datetime.utcnow()
