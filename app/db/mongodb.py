import os
import logging
from datetime import datetime
import pandas as pd

from news import fetch_news_for_ticker, add_sentiment
from pymongo import MongoClient, DESCENDING
from app.config import settings
from dateutil import parser as date_parser

from predictive_model import get_avg_sentiment_for_tickers

logging.basicConfig(
    level=logging.INFO,
    filename="logs/mongodb.log",
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# --- MongoDB setup ---
client = MongoClient(settings.mongo_uri)
mongo_db = client[settings.mongo_db]


def get_collection(name: str):
    return mongo_db[name]


news_col = get_collection("news")


def get_latest_published(ticker: str):
    doc = news_col.find_one({"ticker": ticker}, sort=[("published", DESCENDING)])
    if doc and doc.get("published"):
        return pd.to_datetime(doc["published"])
    return None


def insert_news(items: list):
    """Wstawia listę newsów do kolekcji news w MongoDB"""
    if not items:
        return
    try:
        for item in items:
            if isinstance(item.get("published"), str):
                try:
                    item["published"] = date_parser.parse(item["published"])
                except Exception as e:
                    item["published"] = None
                    print(f"Nie udało się sparsować daty: {e}")
        news_col.insert_many(items)
        print(f"Wstawiono {len(items)} newsów do MongoDB")
    except Exception as e:
        print("Błąd wstawiania newsów:", e)


def insert_news_df(df: pd.DataFrame):
    """Wstawia datafram z newsami do kolekcji do MongoDB"""
    if df.empty:
        logging.info("Brak danych do zapisania (df puste)")
        return
    try:
        records = df.to_dict("records")
        insert_news(records)
    except Exception as e:
        logging.error(f"Błąd wstawiania danych do MongoDB: {e}")


def update_news_for_ticker(ticker: str):
    """Aktualizuje newsy dla pojedynczego tickera"""
    try:
        latest_doc = news_col.find_one(
            {"ticker": ticker},
            sort=[("published", -1)]
        )

        latest = None
        if latest_doc and "published" in latest_doc:
            latest = pd.to_datetime(latest_doc["published"])
            # Jeśli jest tz-aware, zmieniamy na tz-naive
            if latest.tzinfo is not None:
                latest = latest.tz_convert(None) if hasattr(latest, 'tz_convert') else latest.replace(tzinfo=None)

        # pobieranie newsow
        df = fetch_news_for_ticker(ticker)
        if df.empty:
            logging.info(f"Brak nowych newsów dla {ticker}")
            return

        # zmiana dat do tz-naive
        df["published"] = pd.to_datetime(df["published"].apply(
            lambda x: date_parser.parse(x) if pd.notnull(x) else None
        ))
        if df["published"].dt.tz is not None:
            df["published"] = df["published"].dt.tz_localize(None)

        if latest is not None:
            df = df[df["published"] > latest]

        if df.empty:
            logging.info(f"Brak nowych newsów dla {ticker} od {latest}")
            return

        df = add_sentiment(df)

        records = df.to_dict("records")
        insert_news(records)
        logging.info(f"Dodano {len(records)} nowych newsów dla {ticker}")

    except Exception as e:
        logging.error(f"Błąd przy aktualizacji newsów dla {ticker}: {e}")


def update_all_tickers(tickers: list):
    """Aktualizuje newsy dla listy tickerów"""
    for i, t in enumerate(tickers, 1):
        logging.info(f"({i}/{len(tickers)}) Aktualizacja newsów dla {t}")
        update_news_for_ticker(t)

