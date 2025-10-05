
import logging
import os
import sys
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from pymongo import MongoClient

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app.config import settings

# -------- KONFIG --------
NEWS_WINDOW_DAYS = 7
FUTURE_THRESHOLD_PCT = 2.0
CHANGE_THRESHOLD_PCT = 2.0
MODEL_N_ESTIMATORS = 300
MODEL_MAX_DEPTH = 10

OUTPUT_DIR = "outputs"
LOG_DIR = "logs/predictive"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "predictive_model.log")

# -------- LOGOWANIE --------
logger = logging.getLogger("predictive_model")
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(LOG_FILE)
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
fh.setFormatter(fmt)
ch.setFormatter(fmt)

logger.addHandler(fh)
logger.addHandler(ch)

# -------- POŁĄCZENIA DB --------
# jeśli używasz Supabase
DATABASE_URL = f"postgresql://{settings.PG_USER}:{settings.PG_PASSWORD}@{settings.PG_HOST}:5432/{settings.PG_DB}?sslmode=require"

engine = create_engine(DATABASE_URL, echo=False, future=True)

mongo_client = MongoClient(settings.mongo_uri)
mongo_db = mongo_client[settings.mongo_db]
news_col = mongo_db["news"]

# -------- HELPERY --------
def init_predictions_table():
    ddl = """
    CREATE TABLE IF NOT EXISTS stocks_predictions (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR(20),
        company VARCHAR(255),
        potential_score NUMERIC,
        import_date DATE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    logger.info("Tabela stocks_predictions OK")

def load_all_stocks_data() -> pd.DataFrame:
    logger.info("Wczytuję stocks_data z Postgresa...")
    df = pd.read_sql("SELECT * FROM stocks_data", engine)
    if df.empty:
        logger.error("Brak danych w stocks_data")
        return df
    if "import_date" in df.columns:
        df["import_date"] = pd.to_datetime(df["import_date"]).dt.date
    for col in ["market_cap", "p_e", "price", "change", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    logger.info(f"Pobrano {len(df)} rekordów ({df['import_date'].nunique()} dni)")
    logger.debug(f"Kolumny: {df.columns.tolist()}")
    return df

def get_avg_sentiment_for_tickers(tickers, day, window_days=7):
    """
    Średni sentyment z newsów w oknie (domyślnie 7 dni) do danego dnia.
    """
    if not isinstance(day, (datetime, pd.Timestamp)):
        day = pd.to_datetime(day)

    start = day - timedelta(days=window_days)
    end = day + timedelta(days=1)

    cursor = news_col.aggregate([
        {"$addFields": {
            "published_dt": {
                "$cond": {
                    "if": {"$eq": [{"$type": "$published"}, "string"]},
                    "then": {"$toDate": "$published"},
                    "else": "$published"
                }
            }
        }},
        {"$match": {
            "ticker": {"$in": list(tickers)},
            "published_dt": {"$gte": start, "$lt": end}
        }},
        {"$group": {
            "_id": "$ticker",
            "avg_sentiment": {"$avg": "$sentiment"},
            "count": {"$sum": 1}
        }}
    ])

    results = list(cursor)
    if not results:
        logger.info(f"{day.date()}: brak newsów (okno {window_days} dni)")
        return pd.DataFrame(columns=["ticker", "avg_sentiment"])

    df = pd.DataFrame(results)
    df.rename(columns={"_id": "ticker"}, inplace=True)

    logger.info(f"{day.date()}: {len(df)} tickerów z sentymentem (z okna {window_days} dni)")
    return df



def create_forward_label(df_all, day, next_day):
    df_day = df_all[df_all["import_date"] == day].copy()
    if next_day is None:
        logger.info(f"Brak next_day dla {day} — label na podstawie same-day change")
        df_day["high_potential"] = (df_day["change"].fillna(0) > CHANGE_THRESHOLD_PCT).astype(int)
        return df_day
    df_next = df_all[df_all["import_date"] == next_day][["ticker", "price"]].rename(columns={"price": "price_next"})
    merged = df_day.merge(df_next, on="ticker", how="left")
    merged["future_pct"] = (merged["price_next"] - merged["price"]) / merged["price"] * 100
    merged["high_potential"] = np.where(
        merged["price_next"].notna(),
        (merged["future_pct"] > FUTURE_THRESHOLD_PCT).astype(int),
        (merged["change"].fillna(0) > CHANGE_THRESHOLD_PCT).astype(int),
    )
    return merged

# -------- PIPELINE GŁÓWNY --------
def process_historical():
    init_predictions_table()
    df_all = load_all_stocks_data()
    if df_all.empty:
        return

    # filtr podstawowy
    df_all = df_all.dropna(subset=["price", "volume", "market_cap"])
    df_all = df_all[df_all["market_cap"] > 0]

    dates = sorted(df_all["import_date"].unique())
    logger.info(f"Przetwarzam {len(dates)} dni: {dates}")
    all_top_rows = []

    for idx, day in enumerate(dates):
        try:
            next_day = dates[idx + 1] if idx + 1 < len(dates) else None
            logger.info(f"Przetwarzanie dnia {day} (next={next_day})")

            df_day = create_forward_label(df_all, day, next_day)
            tickers = df_day["ticker"].dropna().unique().tolist()
            if not tickers:
                logger.warning(f"Brak tickerów dla {day}, pomijam")
                continue

            sentiment_df = get_avg_sentiment_for_tickers(tickers, day)
            df_day = df_day.merge(sentiment_df, on="ticker", how="left")
            df_day["avg_sentiment"] = df_day["avg_sentiment"].fillna(0.0)

            # cechy
            df_day["market_cap_log"] = np.log1p(df_day["market_cap"].astype(float))
            df_day["volume_log"] = np.log1p(df_day["volume"].astype(float))
            df_day[["price", "p_e", "change"]] = df_day[["price", "p_e", "change"]].fillna(0)

            logger.debug(f"Przykładowe wiersze {day}: {df_day.head(3).to_dict('records')}")
            feature_cols = ["price", "p_e", "market_cap_log", "volume_log", "change", "avg_sentiment"]
            X = df_day[feature_cols].fillna(0)
            y = df_day["high_potential"].fillna(0).astype(int)

            if y.nunique() < 2 or len(df_day) < 5:
                logger.warning(f"Niewystarczająca wariancja labeli dla {day} — fallback scoring")
                p_norm = (X["price"] - X["price"].min()) / (X["price"].max() - X["price"].min() + 1e-9)
                mc_norm = (X["market_cap_log"] - X["market_cap_log"].min()) / (X["market_cap_log"].max() - X["market_cap_log"].min() + 1e-9)
                sentiment_norm = (X["avg_sentiment"] - X["avg_sentiment"].min()) / (abs(X["avg_sentiment"]).max() + 1e-9)
                df_day["potential_score"] = (0.4 * p_norm + 0.4 * mc_norm + 0.2 * sentiment_norm).fillna(0)
            else:
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
                model = RandomForestClassifier(n_estimators=MODEL_N_ESTIMATORS, max_depth=MODEL_MAX_DEPTH, random_state=42)
                model.fit(X_train, y_train)
                y_pred = model.predict(X_test)
                report = classification_report(y_test, y_pred, zero_division=0)
                logger.info(f"{day} classification report:\n{report}")
                df_day["potential_score"] = model.predict_proba(X)[:, 1]

            # top 20
            top_day = df_day.sort_values("potential_score", ascending=False).head(20)
            logger.info(f"Top tickery {day}: {top_day['ticker'].tolist()[:10]}")

            save_cols = ["ticker", "company", "potential_score"]
            top_day_to_save = top_day[save_cols].copy()
            top_day_to_save["import_date"] = pd.to_datetime(day)

            per_day_csv = os.path.join(OUTPUT_DIR, f"top_stocks_predictions_{day}.csv")
            top_day_to_save.to_csv(per_day_csv, index=False)
            logger.debug(f"Zapisano CSV: {per_day_csv}")

            all_top_rows.append(top_day_to_save)

            try:
                top_day_to_save.to_sql("stocks_predictions", engine, if_exists="append", index=False)
                logger.debug(f"Zapisano do DB dla {day}")
            except Exception as e:
                logger.error(f"DB insert error dla {day}: {e}")

        except Exception as e:
            logger.exception(f"Błąd podczas przetwarzania {day}: {e}")

    if all_top_rows:
        combined = pd.concat(all_top_rows, ignore_index=True)
        combined_csv = os.path.join(OUTPUT_DIR, "top_stocks_predictions_all_days.csv")
        combined.to_csv(combined_csv, index=False)
        logger.info(f"Zapisano zbiorcze CSV: {combined_csv}")
    else:
        logger.warning("Brak wyników do zapisania.")

# -------- ENTRYPOINT --------
if __name__ == "__main__":
    logger.info("Start")
    process_historical()
    logger.info("Koniec")
