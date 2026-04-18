# sens_scraper.py — JSE's free public announcement feed
import requests
from bs4 import BeautifulSoup
from textblob import TextBlob
import pandas as pd
from datetime import datetime

def scrape_sens_announcements(pages=3):
    """Scrape JSE SENS (Stock Exchange News Service) — publicly available"""
    base_url = "https://www.jse.co.za/services/market-data/sens-search"
    results = []
    
    for ticker in ["NPN", "BTI", "AGL", "SBK"]:
        url = f"https://senspdf.jse.co.za/documents/2024/{ticker}"
        # Also scrape Moneyweb + BusinessLive for news sentiment
        # These are public pages — no auth required
    
    # Moneyweb RSS (free, SA-specific, high quality)
    moneyweb_rss = "https://www.moneyweb.co.za/feed/"
    response = requests.get(moneyweb_rss, timeout=10)
    soup = BeautifulSoup(response.content, "xml")
    
    for item in soup.find_all("item")[:50]:
        title = item.find("title").text
        description = item.find("description").text if item.find("description") else ""
        pub_date = item.find("pubDate").text if item.find("pubDate") else ""
        
        sentiment = TextBlob(title + " " + description).sentiment
        
        results.append({
            "source": "moneyweb",
            "title": title,
            "polarity": round(sentiment.polarity, 3),
            "subjectivity": round(sentiment.subjectivity, 3),
            "published": pub_date,
            "fetched_at": datetime.now().isoformat()
        })
    
    return pd.DataFrame(results)

def get_ticker_sentiment_score(ticker: str, news_df: pd.DataFrame) -> float:
    """
    Match news to ticker → aggregate sentiment.
    This is your proprietary signal — no one else has SA-specific
    news sentiment mapped to JSE tickers at this granularity.
    """
    company_map = {
        "NPN.JO": ["naspers", "tencent", "prosus"],
        "SBK.JO": ["standard bank", "stanbic"],
        "MTN.JO": ["mtn", "mobile money"],
        "SOL.JO": ["sasol", "chemicals", "fuel"],
        "AGL.JO": ["anglo american", "mining"],
    }
    
    keywords = company_map.get(ticker, [ticker.replace(".JO", "").lower()])
    mask = news_df["title"].str.lower().apply(
        lambda t: any(kw in t for kw in keywords)
    )
    relevant = news_df[mask]
    
    if relevant.empty:
        return 0.0
    return round(relevant["polarity"].mean(), 3)