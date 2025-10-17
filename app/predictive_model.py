# predictive_model.py

import pandas as pd
import numpy as np
from datetime import timedelta, date, datetime
import streamlit as st
from pytz import utc
from sklearn.ensemble import RandomForestClassifier
from pymongo import MongoClient
from supabase import create_client, Client
from postgrest.exceptions import APIError
import re  # Dodajemy import re do czyszczenia danych

from app.db.user_supabase_manager import clean_and_transform_for_db
from app.db.user_mongodb_manager import MongoNewsHandler
from app.stocks import fetch_finviz_for_ticker

# -------- PARAMETRY MODELU --------
NEWS_WINDOW_DAYS = 7
FUTURE_THRESHOLD_PCT = 2.0
CHANGE_THRESHOLD_PCT = 2.0
MODEL_N_ESTIMATORS = 300
MODEL_MAX_DEPTH = 10


def initialize_clients(supabase_url: str, supabase_key: str, mongo_uri: str, mongo_db_name: str):
    supabase_client: Client = create_client(supabase_url, supabase_key)
    mongo_client = MongoClient(mongo_uri)
    db = mongo_client[mongo_db_name]
    news_collection = db["news"]

    return supabase_client, news_collection

@st.cache_data(ttl=3600)
def load_all_stocks_data(_supabase_client: Client):
    """Pobiera dane z Supabase i konwertuje je do DataFrame."""
    try:
        resp = _supabase_client.table("stocks_data").select("*").execute()
        df = pd.DataFrame(resp.data)
        if df.empty:
            return pd.DataFrame()

        for col in ["price", "market_cap", "volume", "change", "p_e"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        if "import_date" in df.columns:
            df["import_date"] = pd.to_datetime(df["import_date"], errors='coerce').dt.date
        df.dropna(subset=["ticker", "price", "market_cap"], inplace=True)
        return df
    except APIError as e:
        st.error(f"Błąd Supabase API: {e}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Nieoczekiwany błąd podczas ładowania danych giełdowych: {e}")
        return pd.DataFrame()


def create_forward_label(df_all, day, next_day):
    """Tworzy etykietę 'high_potential' na podstawie przyszłej ceny."""
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


@st.cache_data(ttl=3600)
def process_historical_analysis(_supabase_client: Client, _news_collection):
    """Przetwarza wszystkie dane historyczne i zwraca ranking tickerów."""
    df_all = load_all_stocks_data(_supabase_client)
    if df_all.empty:
        return pd.DataFrame()

    df_all = df_all.dropna(subset=["price", "volume", "market_cap"])
    df_all = df_all[df_all["market_cap"] > 0]
    dates = sorted(df_all["import_date"].unique())

    if len(dates) < 1:
        return pd.DataFrame()

    all_top = []

    for idx, day in enumerate(dates[:-1]):
        next_day = dates[idx + 1]
        df_day = create_forward_label(df_all, day, next_day)
        tickers = df_day["ticker"].tolist()

        sentiment_df = MongoNewsHandler.get_average_sentiment_for_tickers(tickers, as_of_date=day)
        df_day = df_day.merge(sentiment_df, on="ticker", how="left").fillna(0)

        df_day["market_cap_log"] = np.log1p(df_day["market_cap"])
        df_day["volume_log"] = np.log1p(df_day["volume"])

        features = ["price", "p_e", "market_cap_log", "volume_log", "avg_sentiment"]
        X = df_day[features].fillna(0)
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

    if not all_top:
        return pd.DataFrame()

    result_df = pd.concat(all_top, ignore_index=True)
    result_df = result_df.groupby("ticker", as_index=False).agg({"company": "first", "potential_score": "max"})
    return result_df.sort_values("potential_score", ascending=False).reset_index(drop=True)


def analyze_single_ticker(ticker: str, supabase_client: Client, news_collection):
    """
    Analizuje pojedynczy ticker 'na żywo', trenując model na najnowszych danych historycznych.
    """
    # KROK 1: Pobranie i oczyszczenie danych "na żywo" z Finviz
    try:
        st.write(f"Pobieram najnowsze dane dla **{ticker.upper()}** z Finviz...")
        df_live_raw = fetch_finviz_for_ticker(ticker=ticker.upper())

        if df_live_raw.empty:
            st.error(f"Nie znaleziono danych dla tickera '{ticker.upper()}' w Finviz.")
            return pd.DataFrame()

        df_live_raw.rename(columns={
            'Company': 'company', 'P/E': 'p_e', 'Price': 'price',
            'Change': 'change', 'Volume': 'volume', 'Market Cap': 'market_cap',
            'Ticker': 'ticker'
        }, inplace=True)

        # Zabezpieczenie na wypadek, gdyby scraper nie zwrócił kolumny 'ticker'
        if 'ticker' not in df_live_raw.columns:
            df_live_raw['ticker'] = ticker.upper()

        df_live = clean_and_transform_for_db(df_live_raw)

    except Exception as e:
        st.error(f"Błąd podczas pobierania lub przetwarzania danych live dla {ticker.upper()}: {e}")
        return pd.DataFrame()

    # KROK 2: Załadowanie danych historycznych do treningu
    df_all_history = load_all_stocks_data(supabase_client)
    if df_all_history.empty:
        st.warning("Brak danych historycznych w bazie do wytrenowania modelu. Wynik może być niedokładny.")
        df_live["potential_score"] = "Brak danych do oceny"
        return df_live

    latest_history_date = df_all_history["import_date"].max()
    st.write(f"Używam danych historycznych z dnia **{latest_history_date}** do treningu modelu.")

    df_train = df_all_history[df_all_history["import_date"] == latest_history_date].copy()

    # KROK 3: Przygotowanie danych treningowych (X_train, y_train)
    # Obliczamy sentyment dla WSZYSTKICH spółek z dnia treningowego
    train_tickers = df_train["ticker"].tolist()
    train_sentiment = MongoNewsHandler.get_average_sentiment_for_tickers(
        train_tickers,
        as_of_date=latest_history_date
    )
    df_train = df_train.merge(train_sentiment, on="ticker", how="left").fillna(0)

    df_train["market_cap_log"] = np.log1p(df_train["market_cap"])
    df_train["volume_log"] = np.log1p(df_train["volume"])

    features = ["price", "p_e", "market_cap_log", "volume_log", "change", "avg_sentiment"]
    X_train = df_train[features].fillna(0)
    y_train = (df_train["change"].fillna(0) > CHANGE_THRESHOLD_PCT).astype(int)

    # KROK 4: Przygotowanie danych do predykcji (X_predict)
    # Obliczamy sentyment dla analizowanej spółki z ostatnich 7 dni
    live_sentiment = MongoNewsHandler.get_average_sentiment_for_ticker(
        ticker,
        as_of_date=datetime.now()
    )
    df_live = df_live.merge(live_sentiment, on="ticker", how="left")

    if df_live['avg_sentiment'].isnull().any():
        st.warning(
            f"Nie znaleziono aktualnych wiadomości (z ostatnich {NEWS_WINDOW_DAYS} dni) dla tickera {ticker.upper()}. Sentyment zostanie potraktowany jako neutralny (0).")
        df_live['avg_sentiment'].fillna(0, inplace=True)

    df_live["market_cap_log"] = np.log1p(df_live["market_cap"])
    df_live["volume_log"] = np.log1p(df_live["volume"])
    X_predict = df_live[features].fillna(0)

    # KROK 5: Trening modelu i predykcja
    if y_train.nunique() < 2 or len(df_train) < 10:
        st.warning("Zbyt mało zróżnicowanych danych historycznych do wytrenowania modelu AI. Wynik jest uproszczony.")
        df_live["potential_score"] = 0.5
    else:
        model = RandomForestClassifier(n_estimators=MODEL_N_ESTIMATORS, max_depth=MODEL_MAX_DEPTH, random_state=42,
                                       class_weight='balanced')
        model.fit(X_train, y_train)
        probabilities = model.predict_proba(X_predict)[:, 1]
        df_live["potential_score"] = probabilities
        st.success(f"Analiza AI dla **{ticker.upper()}** zakończona.")

    # KROK 6: Zwrócenie sformatowanych wyników
    final_columns = ["ticker", "company", "price", "change", "p_e", "volume", "potential_score"]
    return df_live[final_columns]


# ==============================================================================
# NOWA FUNKCJA DO WYŚWIETLANIA TOPOWYCH SPÓŁEK
# ==============================================================================

@st.cache_data(ttl=1800)  # Cache na 30 minut, żeby nie obciążać Finviz
def _fetch_and_cache_ticker_data(ticker):
    """Pobiera i cachuje dane dla pojedynczego tickera."""
    return fetch_finviz_for_ticker(ticker)


def display_top_stocks_card_view():
    """
    Pobiera dane dla listy predefiniowanych, popularnych spółek
    i wyświetla je w estetycznym, kafelkowym widoku.
    """
    st.subheader("Przegląd Gigantów Rynku", divider='rainbow')

    # Lista popularnych tickerów, które chcemy wyświetlić
    # Możesz ją dowolnie modyfikować
    top_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "JPM"]

    # Ustawienie 4 kolumn
    cols = st.columns(4)

    # Pętla przez listę tickerów
    for i, ticker in enumerate(top_tickers):
        # Wybór kolumny (cyklicznie od 0 do 3)
        col = cols[i % 4]

        with col:
            with st.spinner(f'Ładuję {ticker}...'):
                try:
                    # Pobieramy dane z Finviz
                    df_raw = _fetch_and_cache_ticker_data(ticker)

                    if df_raw.empty:
                        st.warning(f"Brak danych dla {ticker}")
                        continue

                    # Wyciągamy pierwszy (i jedyny) wiersz z danymi
                    stock_data = df_raw.iloc[0]

                    # Pobieranie kluczowych informacji
                    company_name = stock_data.get('Company', 'Brak nazwy')
                    price_str = stock_data.get('Price', '0')
                    change_str = stock_data.get('Change', '0.00%')
                    volume_str = stock_data.get('Volume', '0')
                    market_cap_str = stock_data.get('Market Cap', '0')

                    # Czyszczenie i konwersja danych
                    price = float(price_str)
                    # Usuwamy '%' i konwertujemy na float
                    change_pct = float(change_str.replace('%', ''))

                    # Dodajemy ikonkę w zależności od zmiany
                    emoji = "📈" if change_pct >= 0 else "📉"

                    # Tworzymy "kartę" za pomocą kontenera z obramowaniem
                    with st.container(border=True):
                        st.markdown(f"##### {emoji} {company_name} ({ticker})")

                        # st.metric to idealny komponent do tego celu
                        st.metric(
                            label="Aktualna Cena",
                            value=f"${price:.2f}",
                            delta=f"{change_str}"
                        )

                        # Dodatkowe informacje
                        st.markdown(f"**Kapitalizacja:** {market_cap_str}")
                        st.markdown(f"**Wolumen:** {volume_str}")

                except Exception as e:
                    st.error(f"Błąd dla {ticker}: {e}")