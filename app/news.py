import os

import requests
import feedparser
import pandas as pd
from urllib.parse import urljoin, quote_plus
from datetime import datetime, timedelta
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging
import time

from save_data import save_news_to_csv
from stocks import fetch_finviz

os.makedirs("logs", exist_ok=True)
logging.basicConfig(level=logging.INFO, filename="logs/news_scraper.log",
                    format="%(asctime)s [%(levelname)s] %(message)s")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
    "DNT": "1"
}


def fetch_google_news_rss(ticker, country='US', lang='en'):
    q = quote_plus(f"{ticker} stock")
    rss = f"https://news.google.com/rss/search?q={q}&hl={lang}-{country}&gl={country}&ceid={country}:{lang}"
    logging.info(f"Pobieram RSS: {rss}")
    feed = feedparser.parse(rss)
    items = []
    for e in feed.entries:
        source = None
        if 'source' in e:
            source = e.source.get('title') if isinstance(e.source, dict) else e.get('source')
        published = e.get('published') or e.get('pubDate') or None
        items.append({
            "ticker": ticker,
            "headline": e.get("title"),
            "link": e.get("link"),
            "source": source,
            "published": published
        })
    df = pd.DataFrame(items)

    logging.info(f"RSS: znaleziono {len(df)} pozycji dla {ticker}")
    return df


def add_sentiment(df, text_col='headline'):
    if df.empty:
        return df
    analyzer = SentimentIntensityAnalyzer()
    df = df.copy()
    df['sentiment'] = df[text_col].fillna("").apply(lambda t: analyzer.polarity_scores(t)['compound'])
    return df


def fetch_news_for_ticker(ticker):
    try:
        news_df = fetch_google_news_rss(ticker)
        if not news_df.empty:
            news_df = add_sentiment(news_df)
            news_df["ticker"] = ticker
            return news_df
    except Exception as e:
        logging.error(f"Google RSS error: {e}")

    # none found
    logging.info(f"Brak newsów dla {ticker} (RSS)")
    return pd.DataFrame()


if __name__ == "__main__":
    only_tickers_df = fetch_finviz(get_only_tickers=True, with_filters=False, max_companies=50)
    tickers = only_tickers_df["Ticker"].tolist()
    ALL = []
    for t in tickers:
        news_df = fetch_news_for_ticker(t)
        news_df["ticker"] = t
        if not news_df.empty:
            ALL.append(news_df)

    if ALL:
        final = pd.concat(ALL, ignore_index=True)
        save_news_to_csv(final)
        logging.info(f"Pobrano {len(final)} newsów dla {len(tickers)} spółek")

        #dodanie do MongoDB
        from db.mongodb import insert_news_df
        insert_news_df(final)
