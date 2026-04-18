import time
import feedparser
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from .base import BaseScraper, Article


class BusinessLiveScraper(BaseScraper):
    """
    BusinessLive (BusinessDay + Sunday Times Business).
    RSS feeds are publicly accessible — article body is partially paywalled
    but headlines + summaries are enough for strong sentiment signal.
    """
    RSS_FEEDS = [
        "https://www.businesslive.co.za/rss/",
        "https://www.businesslive.co.za/bd/markets/rss/",
        "https://www.businesslive.co.za/bd/companies/rss/",
        "https://www.businesslive.co.za/bd/economy/rss/",
    ]
    MAX_ARTICLES_PER_FEED = 15

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def _fetch_feed(self, url: str) -> feedparser.FeedParserDict:
        response = requests.get(url, headers=self.HEADERS, timeout=self.REQUEST_TIMEOUT)
        response.raise_for_status()
        return feedparser.parse(response.content)

    def _extract_summary(self, entry) -> str:
        """BusinessLive puts usable content in the description field."""
        for field in ["summary", "description", "content"]:
            raw = entry.get(field, "")
            if raw:
                if isinstance(raw, list):
                    raw = raw[0].get("value", "")
                clean = BeautifulSoup(raw, "lxml").get_text(strip=True)
                if len(clean) > 30:
                    return clean[:500]
        return ""

    def fetch(self) -> list[Article]:
        articles = []
        seen_urls = set()

        for feed_url in self.RSS_FEEDS:
            try:
                self.logger.info(f"Fetching BusinessLive feed: {feed_url}")
                feed = self._fetch_feed(feed_url)

                for entry in feed.entries[:self.MAX_ARTICLES_PER_FEED]:
                    url = entry.get("link", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    articles.append(Article(
                        source="businesslive",
                        title=entry.get("title", "").strip(),
                        url=url,
                        published_at=self._safe_date(
                            entry.get("published", "") or entry.get("updated", "")
                        ),
                        summary=self._extract_summary(entry),
                        author=entry.get("author", ""),
                    ))
                    self.logger.info(f"  ✓ {articles[-1].title[:60]}...")

                time.sleep(self.RATE_LIMIT_SECONDS)

            except Exception as e:
                self.logger.error(f"BusinessLive feed failed ({feed_url}): {e}")

        self.logger.info(f"BusinessLive: {len(articles)} articles fetched")
        return articles
