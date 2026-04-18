import time
import feedparser
import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential
from .base import BaseScraper, Article


class MoneywebScraper(BaseScraper):
    """
    Moneyweb is SA's best free financial news source.
    RSS gives us headlines + summaries. We optionally fetch full body.
    """
    RSS_FEEDS = [
        "https://www.moneyweb.co.za/feed/",
        "https://www.moneyweb.co.za/category/news/feed/",
        "https://www.moneyweb.co.za/category/investments/feed/",
        "https://www.moneyweb.co.za/category/markets/feed/",
        "https://www.moneyweb.co.za/category/companies-and-deals/feed/",
    ]
    MAX_ARTICLES_PER_FEED = 20
    FETCH_FULL_BODY = True  # set False to be faster/lighter

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    def _fetch_feed(self, url: str) -> feedparser.FeedParserDict:
        self.logger.info(f"Fetching Moneyweb feed: {url}")
        response = requests.get(url, headers=self.HEADERS, timeout=self.REQUEST_TIMEOUT)
        response.raise_for_status()
        return feedparser.parse(response.content)

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=5))
    def _fetch_article_body(self, url: str) -> str:
        """Fetch article body — Moneyweb has a fair amount of free content."""
        try:
            resp = requests.get(url, headers=self.HEADERS, timeout=self.REQUEST_TIMEOUT)
            soup = BeautifulSoup(resp.content, "lxml")
            
            # Moneyweb article body selectors
            content_div = (
                soup.find("div", class_="article-content") or
                soup.find("div", class_="entry-content") or
                soup.find("article")
            )
            if not content_div:
                return ""
            
            # Remove ads, nav, related articles
            for tag in content_div.find_all(["script", "style", "nav", "aside"]):
                tag.decompose()
            
            paragraphs = content_div.find_all("p")
            text = " ".join(p.get_text(strip=True) for p in paragraphs[:8])
            return text[:1500]  # cap at 1500 chars for NLP
        except Exception as e:
            self.logger.warning(f"Body fetch failed for {url}: {e}")
            return ""

    def fetch(self) -> list[Article]:
        articles = []
        seen_urls = set()

        for feed_url in self.RSS_FEEDS:
            try:
                feed = self._fetch_feed(feed_url)
                
                for entry in feed.entries[:self.MAX_ARTICLES_PER_FEED]:
                    url = entry.get("link", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    # Clean HTML from summary
                    raw_summary = entry.get("summary", "")
                    summary = BeautifulSoup(raw_summary, "lxml").get_text(strip=True)

                    article = Article(
                        source="moneyweb",
                        title=entry.get("title", "").strip(),
                        url=url,
                        published_at=self._safe_date(
                            entry.get("published", "") or
                            entry.get("updated", "")
                        ),
                        summary=summary[:500],
                        author=entry.get("author", ""),
                    )

                    if self.FETCH_FULL_BODY and url:
                        time.sleep(self.RATE_LIMIT_SECONDS)
                        article.full_text = self._fetch_article_body(url)

                    articles.append(article)
                    self.logger.info(f"  ✓ {article.title[:60]}...")

                time.sleep(self.RATE_LIMIT_SECONDS)

            except Exception as e:
                self.logger.error(f"Feed failed ({feed_url}): {e}")
                continue

        self.logger.info(f"Moneyweb: {len(articles)} articles fetched")
        return articles
