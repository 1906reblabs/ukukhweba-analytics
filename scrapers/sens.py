import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
from .base import BaseScraper, Article


class SENSScraper(BaseScraper):
    """
    JSE SENS (Stock Exchange News Service) — the highest-signal source.
    Every price-sensitive announcement MUST be published here by law.
    Earnings, dividends, rights issues, CEO changes — all SENS first.
    
    JSE provides a public search interface. We scrape the results.
    This gives you a LEGAL, DIRECT signal feed before retail investors
    read it on Moneyweb or BusinessLive. This is your moat edge.
    """
    # JSE's public SENS search — no auth required
    SENS_BASE_URL = "https://www.jse.co.za/services/market-data/sens-search"
    
    # Alternative: profiledata.co.za has a free SENS RSS endpoint
    PROFILE_DATA_RSS = "https://www.profiledata.co.za/Modules/RealTimeDelay/RealTimeDelayRSS.aspx?Key=sens"
    
    # Backup: Sharenet SENS feed (free, delayed 15 min)
    SHARENET_SENS = "https://www.sharenet.co.za/v3/sens.php"

    # JSE tickers to monitor — expand this list over time
    MONITORED_TICKERS = [
        "NPN", "PRX", "BTI", "AGL", "SBK", "FSR", "SOL", "MTN",
        "VOD", "BHP", "IMP", "AMS", "GLD", "ABG", "NED", "INL",
        "TBS", "CPI", "SPP", "REM", "MNP", "ARI", "EXX", "SHP",
        "WHL", "PIK", "DSY", "DIS", "LHC", "TFG", "MRP", "FBR",
    ]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=3, max=15))
    def _fetch_sharenet_sens(self) -> list[Article]:
        """
        Sharenet provides a table of recent SENS announcements.
        Publicly accessible, no login required.
        """
        articles = []
        response = requests.get(
            self.SHARENET_SENS,
            headers={**self.HEADERS, "Accept": "text/html"},
            timeout=self.REQUEST_TIMEOUT,
            params={"show": "50"}
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "lxml")

        # Parse SENS table
        table = soup.find("table", id="sens") or soup.find("table", class_="sens")
        if not table:
            # Fallback: find any table with SENS-like data
            tables = soup.find_all("table")
            table = tables[0] if tables else None

        if not table:
            self.logger.warning("No SENS table found on Sharenet")
            return []

        rows = table.find_all("tr")[1:]  # skip header
        for row in rows[:50]:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue
            try:
                date_str = cols[0].get_text(strip=True)
                ticker   = cols[1].get_text(strip=True).upper().replace(" ", "")
                headline = cols[2].get_text(strip=True)
                link_tag = cols[2].find("a")
                url = f"https://www.sharenet.co.za{link_tag['href']}" if link_tag else ""

                articles.append(Article(
                    source="sens",
                    title=f"[SENS] {ticker}: {headline}",
                    url=url,
                    published_at=self._safe_date(date_str),
                    summary=headline,
                    full_text=headline,
                ))
            except Exception as e:
                self.logger.debug(f"Row parse error: {e}")
                continue

        return articles

    @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=2, max=8))
    def _fetch_profiledata_sens(self) -> list[Article]:
        """
        ProfileData RSS feed for SENS — more reliable format.
        Falls back to this if Sharenet changes its structure.
        """
        import feedparser
        response = requests.get(
            self.PROFILE_DATA_RSS,
            headers=self.HEADERS,
            timeout=self.REQUEST_TIMEOUT
        )
        feed = feedparser.parse(response.content)
        articles = []

        for entry in feed.entries[:50]:
            title = entry.get("title", "")
            articles.append(Article(
                source="sens",
                title=f"[SENS] {title}",
                url=entry.get("link", ""),
                published_at=self._safe_date(entry.get("published", "")),
                summary=entry.get("summary", title)[:500],
                full_text=entry.get("summary", "")[:1000],
            ))

        return articles

    def fetch(self) -> list[Article]:
        articles = []

        # Try primary source
        try:
            articles = self._fetch_sharenet_sens()
            self.logger.info(f"SENS (Sharenet): {len(articles)} announcements")
        except Exception as e:
            self.logger.warning(f"Sharenet SENS failed: {e}. Trying ProfileData...")
            try:
                articles = self._fetch_profiledata_sens()
                self.logger.info(f"SENS (ProfileData): {len(articles)} announcements")
            except Exception as e2:
                self.logger.error(f"Both SENS sources failed: {e2}")

        return articles
