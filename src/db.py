from pymongo import MongoClient
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# 1. Połączenie
client = MongoClient("mongodb://localhost:27017/")
db = client["stocks_db"]
news_collection = db["news_for_investments"]

# 2. Pobranie newsów
news_df = pd.DataFrame(list(news_collection.find()))

# 3. Analiza sentymentu
analyzer = SentimentIntensityAnalyzer()
news_df['sentiment'] = news_df['headline'].apply(lambda x: analyzer.polarity_scores(x)['compound'])

print(news_df[['ticker', 'headline', 'sentiment']])