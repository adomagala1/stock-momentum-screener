# app/db/user_mongodb_manager.py
import pandas as pd
from pymongo import MongoClient

from app.db.mongodb import news_col, get_average_sentiment, get_latest_published, update_news_for_ticker, update_all_tickers
from app.news import add_sentiment
import streamlit as st
from dateutil import parser as date_parser


class MongoNewsHandler:
    def __init__(self, mongo_uri=None, mongo_db=None, collection_name="news_db"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[mongo_db]
        self.collection = self.db[collection_name]

    def get_collection(self):
        return self.db["news"]

    def fetch_news(self, tickers: list):
        """Pobiera newsy z Mongo dla listy tickerów"""
        dfs = []
        for ticker in tickers:
            docs = list(self.collection.find({"ticker": ticker}))
            if docs:
                df = pd.DataFrame(docs)
                dfs.append(df)
        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()

    def insert_news(self, items: list):
        """Wstawia listę newsów do kolekcji news w MongoDB"""
        if not items:
            return 0
        try:
            for item in items:
                if isinstance(item.get("published"), str):
                    try:
                        item["published"] = date_parser.parse(item["published"])
                    except Exception as e:
                        item["published"] = None
                        print(f"Nie udało się sparsować daty: {e}")

            result = self.collection.insert_many(items)
            inserted_count = len(result.inserted_ids)
            print(f"Wstawiono {inserted_count} newsów do MongoDB")
            return inserted_count

        except Exception as e:
            print("Błąd wstawiania newsów:", e)
            return 0

    def update_news_for_ticker(self, ticker: str):
        """Aktualizuje newsy dla danego tickera"""
        update_news_for_ticker(ticker)

    def update_all_tickers(self, tickers: list):
        """Aktualizuje newsy dla wszystkich tickerów"""
        update_all_tickers(tickers)

    def get_latest_date(self, ticker: str):
        """Zwraca najnowszą datę publikacji dla danego tickera"""
        return get_latest_published(ticker)

    def get_average_sentiment_for_tickers(self, tickers: list):
        """Średni sentiment dla listy tickerów -> zawsze DataFrame"""
        data = []
        for ticker in tickers:
            avg = get_average_sentiment(ticker) or 0
            data.append({"ticker": ticker, "avg_sentiment": avg})
        return pd.DataFrame(data)

    def get_average_sentiment_for_ticker(self, ticker: str):
        """Średni sentiment dla pojedynczego tickera -> DataFrame"""
        avg = get_average_sentiment(ticker) or 0
        return pd.DataFrame([{"ticker": ticker, "avg_sentiment": avg}])