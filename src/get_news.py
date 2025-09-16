import requests
from bs4 import BeautifulSoup
import logging
from pymongo import MongoClient
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}


import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
}

def fetch_yahoo_news(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}?p={ticker}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Znajdź wszystkie li o klasie stream-item
    items = soup.find_all("li", class_="stream-item")
    if not items:
        logging.info("Nie znaleziono żadnych newsów.")
        return pd.DataFrame()

    all_data = []
    for item in items:
        container = item.find("section", class_="container")
        if container:
            a_tag = container.find("a")
            if a_tag:
                link = a_tag.get("href")
                text = a_tag.get_text(strip=True)
                all_data.append({"Text": text, "Link": link})

    df = pd.DataFrame(all_data)
    logging.info(f"Pobrano {len(df)} newsów dla ticker={ticker}.")
    return df

# Przykład użycia:
# df_news = fetch_yahoo_news("AAPL")
# print(df_news.head())



# --- Funkcja licząca sentyment ---
def add_sentiment(news_list):
    analyzer = SentimentIntensityAnalyzer()
    for news in news_list:
        news['sentiment'] = analyzer.polarity_scores(news['headline'])['compound']
    return news_list


# --- Funkcja zapisująca do MongoDB ---
def save_to_mongo(news_list):
    client = MongoClient("mongodb://localhost:27017/")
    db = client["stocks_db"]
    collection = db["news_for_investments"]
    if news_list:
        collection.insert_many(news_list)
        logging.info(f"Wstawiono {len(news_list)} newsów do MongoDB")


# --- Główny workflow ---
if __name__ == "__main__":
    tickers = ["AAPL", "MSFT", "TSLA", "DLO"]  # przykładowe tickery
    all_news = []

    for ticker in tickers:
        try:
            news = fet(ticker)
            news = add_sentiment(news)
            all_news.extend(news)
        except Exception as e:
            logging.error(f"Błąd przy pobieraniu newsów dla {ticker}: {e}")

    save_to_mongo(all_news)

    # Podgląd
    df = pd.DataFrame(all_news)
    print(df[['ticker', 'headline', 'sentiment', 'date', 'source']])
    logging.info("get_news.py zakończony")
