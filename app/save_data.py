# app/save_data.py
import os
import pandas as pd
import logging
from datetime import datetime
import streamlit as st
from app.db.supabase_manager import *



def convert_market_cap(value):
    """Bezpiecznie konwertuje string z kapitalizacją rynkową na liczbę float."""
    if pd.isna(value):
        return None
    value = str(value).strip()
    try:
        if value.endswith('B'):
            return float(value[:-1]) * 1_000_000_000
        elif value.endswith('M'):
            return float(value[:-1]) * 1_000_000
        elif value.endswith('K'):
            return float(value[:-1]) * 1_000
        else:
            return float(value)
    except (ValueError, TypeError):
        return None


def save_stocks_to_csv(df: pd.DataFrame, get_only_tickers=False, with_filters=False) -> None:
    """
    Inteligentnie zapisuje dane giełdowe do CSV, obsługując tryb pełny i 'tylko tickery'.
    """
    if df is None or df.empty:
        logging.warning("Otrzymano pusty DataFrame. Pomijam zapis do pliku.")
        return
    today_str = datetime.now().strftime("%Y%m%d")

    if get_only_tickers:
        logging.info("Tryb 'Tylko tickery'. Zapisywanie uproszczonych danych.")

        path_dir = os.path.join("data", "tickers", today_str)
        filename_suffix = f"finviz_{'filtered_' if with_filters else ''}tickers_{today_str}.csv"

        df_to_save = df[["No", "Ticker"]].copy()

    else:
        logging.info("Tryb pełnych danych. Przetwarzanie i zapisywanie szczegółowych informacji.")

        path_dir = os.path.join("data", "stocks", today_str)
        filename_suffix = f"finviz_{'filtered_' if with_filters else ''}stocks_{today_str}.csv"
        df_to_save = df.copy()
        if "Market Cap" in df_to_save.columns:
            logging.info(f"Kolumny w DataFrame: {df_to_save.columns.tolist()}")
            logging.info(
                f"Pierwsze 5 wartości 'Market Cap' (przed konwersją): {df_to_save['Market Cap'].head().tolist()}")
            df_to_save['market_cap_numeric'] = df_to_save['Market Cap'].apply(convert_market_cap)
            logging.info(
                f"Pierwsze 5 wartości 'market_cap_numeric' (po konwersji): {df_to_save['market_cap_numeric'].head().tolist()}")

        numeric_cols = ["Price", "Volume", "52w High", "52w Low", "P/E", "Rel Vol"]
        for col in numeric_cols:
            if col in df_to_save.columns:
                df_to_save[col] = pd.to_numeric(df_to_save[col].astype(str).str.replace(",", "", regex=False),
                                                errors="coerce")

        percent_cols = ["EPS next 5Y", "Perf Week", "Perf Month", "Change"]
        for col in percent_cols:
            if col in df_to_save.columns:
                df_to_save[col] = pd.to_numeric(df_to_save[col].astype(str).str.replace("%", "", regex=False),
                                                errors="coerce") / 100.0

    try:
        os.makedirs(path_dir, exist_ok=True)
        full_path = os.path.join(path_dir, filename_suffix)

        df_to_save.to_csv(full_path, index=False)
        logging.info(f"Dane pomyślnie zapisane do: {full_path}")
        st.toast(f"Zapisano plik: {filename_suffix}", icon="💾")

    except Exception as e:
        logging.error(f"Nie udało się zapisać pliku {filename_suffix}. Błąd: {e}")
        st.error(f"Błąd zapisu pliku: {e}")


def save_news_to_csv(df: pd.DataFrame, filename_prefix: str = "news_data") -> None:
    """Zapisuje newsy do pliku CSV"""
    if df.empty:
        logging.info("Brak danych newsowych do zapisania (DataFrame jest pusty).")
        return

    folder = os.path.join("data", "news")
    os.makedirs(folder, exist_ok=True)

    columns_order = ["ticker", "headline", "link", "source", "published", "sentiment"]
    df_to_save = df[[col for col in columns_order if col in df.columns]]

    today = datetime.now().strftime("%Y%m%d")
    path = os.path.join(folder, f"{filename_prefix}_{today}.csv")

    try:
        df_to_save.to_csv(path, index=False)
        logging.info(f"Dane newsowe zapisane do {path}")
    except Exception as e:
        logging.error(f"Błąd zapisu pliku newsów: {e}")
        st.error(f"Błąd zapisu pliku newsów: {e}")



