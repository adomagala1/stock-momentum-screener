import os
import requests
import feedparser
import pandas as pd
from urllib.parse import urljoin, quote_plus
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import logging

# Te importy mogą powodować błąd cykliczny, jeśli są na górze.
# Lepiej je przenieść do bloku __main__ lub do funkcji, które ich używają.
# from app.save_data import save_news_to_csv
# from app.stocks import fetch_finviz

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

def fetch_google_news_rss(ticker, country='US', lang='en', limit=10):
    q = quote_plus(f"{ticker} stock")
    rss = f"https://news.google.com/rss/search?q={q}&hl={lang}-{country}&gl={country}&ceid={country}:{lang}"
    logging.info(f"Pobieram RSS: {rss}")
    feed = feedparser.parse(rss)

    items = []
    entries = feed.entries[:limit]

    for e in entries:
        source = None
        if 'source' in e:
            source = e.source.get('title') if isinstance(e.source, dict) else e.get('source')
        published = e.get('published') or e.get('pubDate') or None

        items.append({
            "ticker": ticker,
            "title": e.get("title"),
            "link": e.get("link"),
            "source": source,
            "published": published
        })

    df = pd.DataFrame(items)
    logging.info(f"RSS: znaleziono {len(df)} pozycji dla {ticker}")
    return df


def add_sentiment(df, text_col='title'): # <-- ZMIANA 2: Domyślna kolumna to teraz "title"
    if df.empty:
        return df
    analyzer = SentimentIntensityAnalyzer()
    df = df.copy()
    if text_col in df.columns:
        df['sentiment'] = df[text_col].fillna("").apply(lambda t: analyzer.polarity_scores(t)['compound'])
    else:
        logging.warning(f"W DataFrame brakuje kolumny '{text_col}' do analizy sentymentu.")
        df['sentiment'] = 0.0
    return df


def fetch_news_for_ticker(ticker):
    """Pobiera i analizuje newsy dla pojedynczego tickera."""
    try:
        news_df = fetch_google_news_rss(ticker)
        if not news_df.empty:
            # Wywołanie add_sentiment() automatycznie użyje teraz poprawnej kolumny 'title'
            news_df = add_sentiment(news_df)
            news_df["ticker"] = ticker
            return news_df
    except Exception as e:
        logging.error(f"Błąd podczas pobierania newsów RSS dla {ticker}: {e}")

    logging.info(f"Brak newsów dla {ticker} (RSS)")
    return pd.DataFrame()


if __name__ == "__main__":
    # Importy przeniesione tutaj, aby uniknąć problemów z cyklicznym importem
    from app.save_data import save_news_to_csv
    from app.stocks import fetch_finviz
    from db.mongodb import insert_news_df

    only_tickers_df = fetch_finviz(get_only_tickers=True, with_filters=False, max_companies=50)
    tickers = only_tickers_df["Ticker"].tolist()
    all_news = []
    for t in tickers:
        news_df = fetch_news_for_ticker(t)
        if not news_df.empty:
            all_news.append(news_df)

    if all_news:
        final_df = pd.concat(all_news, ignore_index=True)
        save_news_to_csv(final_df)
        logging.info(f"Pobrano {len(final_df)} newsów dla {len(tickers)} spółek")

        # Dodanie do MongoDB
        insert_news_df(final_df)