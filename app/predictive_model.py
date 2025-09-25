# predictive_model.py

import logging
import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from app.config import settings
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report


logging.basicConfig(level=logging.INFO, filename="logs/predictive_model.log",
                    format="%(asctime)s [%(levelname)s] %(message)s")

DATABASE_URL = f"postgresql://{settings.pg_user}:{settings.pg_password}@127.0.0.1:{settings.pg_port}/{settings.pg_db}"
engine = create_engine(DATABASE_URL, echo=False, future=True)


query = """
SELECT *
FROM stocks_data
WHERE import_date = (SELECT MAX(import_date) FROM stocks_data)
"""
df = pd.read_sql(query, engine)
logging.info(f"Pobrano {len(df)} rekordów ze stocks_data")

df['price_52w_ratio'] = df['price'] / df['fifty_two_week_high']

# Logarytm z kapitalizacji rynku
df['market_cap_log'] = df['market_cap'].apply(lambda x: np.log1p(x) if pd.notna(x) else 0)

# Konwersja kolumn procentowych
percent_cols = ['eps_next_5y_perc', 'perf_week_perc', 'perf_month_perc', 'change_perc']
for col in percent_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)


try:
    news_df = pd.read_sql("SELECT ticker, AVG(sentiment) as avg_sentiment FROM news GROUP BY ticker", engine)
    df = df.merge(news_df, on='ticker', how='left')
except Exception as e:
    logging.warning(f"Nie udało się pobrać sentymentu: {e}")
    df['avg_sentiment'] = 0

u
df['high_potential'] = (df['perf_month_perc'] > 5).astype(int)


features = ['price', 'volume', 'market_cap_log', 'p_e', 'price_52w_ratio', 'avg_sentiment']
X = df[features].fillna(0)
y = df['high_potential']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

model = RandomForestClassifier(n_estimators=300, max_depth=10, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
logging.info("Raport klasyfikacji:\n" + classification_report(y_test, y_pred))


df['potential_score'] = model.predict_proba(X)[:, 1]
top_companies = df.sort_values(by='potential_score', ascending=False).head(20)
logging.info("Top 20 spółek według potencjału:\n" + top_companies[['ticker','company','potential_score']].to_string())

try:
    top_companies[['ticker','company','potential_score']].to_sql(
        'stocks_predictions', engine, if_exists='replace', index=False
    )
    logging.info("Zapisano ranking spółek do tabeli stocks_predictions")
except Exception as e:
    logging.error(f"Błąd przy zapisie do bazy: {e}")


top_companies[['ticker','company','potential_score']].to_csv('top_stocks_predictions.csv', index=False)
logging.info("Zapisano ranking spółek do top_stocks_predictions.csv")
