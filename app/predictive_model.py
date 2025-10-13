import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from postgrest.exceptions import APIError
from sklearn.ensemble import RandomForestClassifier
from pymongo import MongoClient
from supabase import create_client, Client

import load_demo_data
from load_demo_data import load_demo_secrets

# -------- PARAMETRY --------
NEWS_WINDOW_DAYS = 7
FUTURE_THRESHOLD_PCT = 2.0
CHANGE_THRESHOLD_PCT = 2.0
MODEL_N_ESTIMATORS = 300
MODEL_MAX_DEPTH = 10

load_demo_data.load_demo_secrets()

supabase: Client = create_client(st.session_state["sb_url"], st.session_state["sb_api"])
mongo_client = MongoClient(st.session_state["mongo_uri"])
news_col = mongo_client[st.session_state["mongo_db"]].news


# -------- FUNKCJE --------
def load_all_stocks_data(supabase=st.session_state.get("supabase_client")):
    """Pobiera dane ze Supabase (tabela 'stocks_data') i konwertuje je do DataFrame"""
    try:
        resp = supabase.table("stocks_data").select("*").execute()
        data = resp.data  # lista słowników
        if not data:
            st.warning("Brak danych w tabeli 'stocks_data'.")
            return pd.DataFrame()

        df = pd.DataFrame(data)

        # Konwersja kolumn liczbowych
        for col in ["price", "market_cap", "volume", "change", "p_e"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Konwersja daty
        if "import_date" in df.columns:
            df["import_date"] = pd.to_datetime(df["import_date"], errors='coerce').dt.date

        # Usuń wiersze bez kluczowych danych
        df.dropna(subset=["ticker", "price", "market_cap"], inplace=True)
        return df

    except APIError as e:
        st.error(f"Błąd Supabase: {e}")
        return pd.DataFrame()


def get_avg_sentiment(tickers, day, window=NEWS_WINDOW_DAYS):
    if not tickers:
        return pd.DataFrame(columns=["ticker", "avg_sentiment"])
    day = pd.to_datetime(day)
    start = day - timedelta(days=window)
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
        {"$match": {"ticker": {"$in": tickers}, "published_dt": {"$gte": start, "$lt": end}}},
        {"$group": {"_id": "$ticker", "avg_sentiment": {"$avg": "$sentiment"}}}
    ])
    df = pd.DataFrame(list(cursor))
    if df.empty:
        return pd.DataFrame(columns=["ticker", "avg_sentiment"])
    df.rename(columns={"_id": "ticker"}, inplace=True)
    return df[["ticker", "avg_sentiment"]]


def create_forward_label(df_all, day, next_day):
    df_day = df_all[df_all["import_date"] == day].copy()
    if next_day is None:
        df_day["high_potential"] = (df_day["change"].fillna(0) > CHANGE_THRESHOLD_PCT).astype(int)
        return df_day
    df_next = df_all[df_all["import_date"] == next_day][["ticker", "price"]].rename(columns={"price": "price_next"})
    merged = df_day.merge(df_next, on="ticker", how="left")
    merged["future_pct"] = (merged["price_next"] - merged["price"]) / (merged["price"] + 1e-9) * 100
    merged["high_potential"] = np.where(
        merged["price_next"].notna(),
        (merged["future_pct"] > FUTURE_THRESHOLD_PCT).astype(int),
        (merged["change"].fillna(0) > CHANGE_THRESHOLD_PCT).astype(int)
    )
    return merged


def create_forward_label(df_all, day, next_day):
    df_day = df_all[df_all["import_date"] == day].copy()
    if next_day is None:
        df_day["high_potential"] = (df_day["change"].fillna(0) > CHANGE_THRESHOLD_PCT).astype(int)
        return df_day
    df_next = df_all[df_all["import_date"] == next_day][["ticker", "price"]].rename(columns={"price": "price_next"})
    merged = df_day.merge(df_next, on="ticker", how="left")
    merged["future_pct"] = (merged["price_next"] - merged["price"]) / (merged["price"] + 1e-9) * 100
    merged["high_potential"] = np.where(
        merged["price_next"].notna(),
        (merged["future_pct"] > FUTURE_THRESHOLD_PCT).astype(int),
        (merged["change"].fillna(0) > CHANGE_THRESHOLD_PCT).astype(int)
    )
    return merged


def process_historical():
    df_all = load_all_stocks_data(supabase)
    if df_all.empty:
        st.warning("Brak danych w tabeli stocks")
        return
    df_all = df_all.dropna(subset=["price", "volume", "market_cap"])
    df_all = df_all[df_all["market_cap"] > 0]
    dates = sorted(df_all["import_date"].unique())
    all_top = []

    for idx, day in enumerate(dates):
        next_day = dates[idx + 1] if idx + 1 < len(dates) else None
        df_day = create_forward_label(df_all, day, next_day)
        tickers = df_day["ticker"].tolist()
        sentiment_df = get_avg_sentiment(tickers, day)
        df_day = df_day.merge(sentiment_df, on="ticker", how="left").fillna(0)
        df_day["market_cap_log"] = np.log1p(df_day["market_cap"])
        df_day["volume_log"] = np.log1p(df_day["volume"])
        X = df_day[["price", "p_e", "market_cap_log", "volume_log", "change", "avg_sentiment"]].fillna(0)
        y = df_day["high_potential"].fillna(0).astype(int)
        if y.nunique() < 2 or len(df_day) < 5:
            p_norm = (X["price"] - X["price"].min()) / (X["price"].max() - X["price"].min() + 1e-9)
            mc_norm = (X["market_cap_log"] - X["market_cap_log"].min()) / (
                    X["market_cap_log"].max() - X["market_cap_log"].min() + 1e-9)
            sentiment_norm = (X["avg_sentiment"] - X["avg_sentiment"].min()) / (abs(X["avg_sentiment"]).max() + 1e-9)
            df_day["potential_score"] = (0.4 * p_norm + 0.4 * mc_norm + 0.2 * sentiment_norm).fillna(0)
        else:
            model = RandomForestClassifier(n_estimators=MODEL_N_ESTIMATORS, max_depth=MODEL_MAX_DEPTH, random_state=42)
            model.fit(X, y)
            df_day["potential_score"] = model.predict_proba(X)[:, 1]
        top = df_day.sort_values("potential_score", ascending=False).head(20)
        all_top.append(top[["ticker", "company", "potential_score"]])

    if all_top:
        result_df = pd.concat(all_top, ignore_index=True)
        result_df["ticker"] = result_df["ticker"].astype(str).str.upper()
        result_df = result_df.groupby("ticker", as_index=False).agg({
            "company": "first",
            "potential_score": "max"
        }).sort_values("potential_score", ascending=False)
        st.dataframe(result_df)
    else:
        st.warning("Brak wyników do wyświetlenia")


def analyze_single_ticker(ticker: str, date=None):
    """Analizuje jeden ticker, pobiera dane, newsy i liczy potencjał"""
    df_all = load_all_stocks_data(supabase)
    if df_all.empty:
        st.warning("Brak danych w tabeli stocks")
        return

    df_all = df_all.dropna(subset=["price", "volume", "market_cap"])
    df_all = df_all[df_all["market_cap"] > 0]

    if date is None:
        date = df_all["import_date"].max()

    next_day = None
    dates = sorted(df_all["import_date"].unique())
    if date in dates:
        idx = dates.index(date)
        if idx + 1 < len(dates):
            next_day = dates[idx + 1]

    df_day = create_forward_label(df_all, date, next_day)
    df_day = df_day[df_day["ticker"].str.upper() == ticker.upper()]

    if df_day.empty:
        st.warning(f"Brak danych dla tickera {ticker} w dniu {date}")
        return

    # Pobieramy sentyment
    sentiment_df = get_avg_sentiment([ticker], date)
    df_day = df_day.merge(sentiment_df, on="ticker", how="left").fillna(0)

    df_day["market_cap_log"] = np.log1p(df_day["market_cap"])
    df_day["volume_log"] = np.log1p(df_day["volume"])

    X = df_day[["price", "p_e", "market_cap_log", "volume_log", "change", "avg_sentiment"]].fillna(0)
    y = df_day["high_potential"].fillna(0).astype(int)

    if y.nunique() < 2 or len(df_day) < 5:
        p_norm = (X["price"] - X["price"].min()) / (X["price"].max() - X["price"].min() + 1e-9)
        mc_norm = (X["market_cap_log"] - X["market_cap_log"].min()) / (
                X["market_cap_log"].max() - X["market_cap_log"].min() + 1e-9)
        sentiment_norm = (X["avg_sentiment"] - X["avg_sentiment"].min()) / (abs(X["avg_sentiment"]).max() + 1e-9)
        df_day["potential_score"] = (0.4 * p_norm + 0.4 * mc_norm + 0.2 * sentiment_norm).fillna(0)
    else:
        model = RandomForestClassifier(n_estimators=MODEL_N_ESTIMATORS, max_depth=MODEL_MAX_DEPTH, random_state=42)
        model.fit(X, y)
        df_day["potential_score"] = model.predict_proba(X)[:, 1]

    st.dataframe(df_day[["ticker", "company", "price", "change", "potential_score"]])
