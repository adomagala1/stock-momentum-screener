# web.py
import streamlit as st
import pandas as pd
from datetime import datetime
from stock_scraper import fetch_finviz
from save_data import save_stocks_csv
from scrape_news import fetch_google_news_rss, add_sentiment
import time

# 🔧 Konfiguracja strony
st.set_page_config(page_title="Finviz Screener", layout="wide", page_icon="📊")

# 🏷️ Custom CSS dla lepszego wyglądu
st.markdown(
    """
    <style>
    .main {
        background-color: #f7f9fc;
    }
    .stMetric {
        background: white;
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# 🏷️ Tytuł
st.title("📊 Finviz Stock Screener")
st.caption("⚡ Interaktywny dashboard do pobierania danych giełdowych i newsów")

# 📌 Panel boczny (ustawienia)
st.sidebar.header("⚙️ Ustawienia")
max_companies = st.sidebar.number_input(
    "Ilość spółek do pobrania (0 = wszystkie)",
    min_value=0, value=0, step=10
)
with_filters = st.sidebar.checkbox("Filtry (Mid Cap, NASDAQ, Rel Volume > 1.5)", value=True)
get_only_tickers = st.sidebar.checkbox("Tylko tickery?", value=False)

# Zakładki
tab1, tab2 = st.tabs(["📈 Statystyki spółek", "📰 Newsy giełdowe"])

# 📈 Zakładka 1 – Statystyki spółek
with tab1:
    st.header("📊 Statystyki spółek")
    if st.button("🚀 Pobierz dane statystyczne"):
        progress = st.progress(0)
        with st.spinner("⏳ Pobieram dane ze screenera..."):
            for i in range(100):
                time.sleep(0.01)
                progress.progress(i + 1)
            df = fetch_finviz(max_companies=max_companies, with_filters=with_filters, get_only_tickers=get_only_tickers)

        if not df.empty:
            st.success(f"✅ Pobrano {len(df)} spółek")
            st.dataframe(df, use_container_width=True)

            # Zapis
            save_stocks_csv(df, get_only_tickers=get_only_tickers, with_filters=with_filters)
            st.info("💾 Dane zapisane do folderu `data` jako CSV")

            today = datetime.now().strftime("%Y%m%d")
            if get_only_tickers and not with_filters:
                filename = f"finviz_tickers_{today}.csv"
            elif not get_only_tickers and not with_filters:
                filename = f"finviz_stocks_{today}.csv"
            else:
                filename = f"finviz_filtered_stocks_{today}.csv"

            with open(f"data/{filename}", "rb") as f:
                st.download_button("⬇️ Pobierz CSV", f, file_name=filename, mime="text/csv")
        else:
            st.warning("⚠️ Nie udało się pobrać danych o spółkach.")

# 📰 Zakładka 2 – Newsy giełdowe
with tab2:
    st.header("📰 Najnowsze newsy ze spółek")
    if st.button("📡 Pobierz newsy"):
        with st.spinner(" (1/2) Pobieram listę tickerów..."):
            df_tickers = fetch_finviz(
                max_companies=max_companies,
                with_filters=with_filters,
                get_only_tickers=True
            )
        tickers = df_tickers["Ticker"].dropna().unique().tolist()

        with st.spinner(" (2/2) Pobieram newsy z Google News..."):
            all_news = []
            for t in tickers:
                df_news = fetch_google_news_rss(t)
                if not df_news.empty:
                    all_news.append(df_news)

            if all_news:
                news = pd.concat(all_news, ignore_index=True)
            else:
                news = pd.DataFrame()

        if not news.empty:
            news = add_sentiment(news)
            st.success(f"✅ Pobrano {len(news)} newsów dla {len(tickers)} spółek")

            # Wyświetl dane
            st.dataframe(news, use_container_width=True)

            # 🔥 Animowane metryki
            avg_sent = news['sentiment'].mean()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🙂 Średni sentyment newsów", f"{avg_sent:.2f}")
            with col2:
                st.metric("📰 Liczba spółek", len(tickers))
        else:
            st.warning("⚠️ Brak newsów do wyświetlenia.")
