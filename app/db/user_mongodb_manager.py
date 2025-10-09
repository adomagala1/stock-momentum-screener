# app/db/user_mongodb_manager.py
import pandas as pd
from app.db.mongodb import news_col, insert_news, get_latest_published, update_news_for_ticker, update_all_tickers
from app.news import add_sentiment

class MongoNewsHandler:
    def __init__(self, collection=news_col, mongo_uri=None, mongo_db=None):
        self.collection = collection

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
        """Dodaje newsy (słownikowe listy) do Mongo i liczy sentyment"""
        if not items:
            return
        for item in items:
            if 'sentiment' not in item:
                df_temp = pd.DataFrame([item])
                df_temp = add_sentiment(df_temp)
                item['sentiment'] = df_temp.loc[0, 'sentiment']
        insert_news(items)

    def update_news_for_ticker(self, ticker: str):
        """Aktualizuje newsy dla danego tickera"""
        update_news_for_ticker(ticker)

    def update_all_tickers(self, tickers: list):
        """Aktualizuje newsy dla wszystkich tickerów"""
        update_all_tickers(tickers)

    def get_latest_date(self, ticker: str):
        """Zwraca najnowszą datę publikacji dla danego tickera"""
        return get_latest_published(ticker)
