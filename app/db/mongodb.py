import os
import logging
from datetime import datetime
import pandas as pd
from pymongo import MongoClient
from app.config import settings
from dateutil import parser as date_parser



# --- MongoDB setup ---
client = MongoClient(settings.mongo_uri)
mongo_db = client[settings.mongo_db]


def get_collection(name: str):
    return mongo_db[name]


news_col = get_collection("news")


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

