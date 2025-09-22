# web.py
import streamlit as st
import pandas as pd
from datetime import datetime
from stock_scraper import fetch_finviz
from save_data import save_stocks_csv, save_news_csv
from scrape_news import fetch_google_news_rss, add_sentiment

# 🎨 Konfiguracja strony
st.set_page_config(page_title="📊 Finviz Screener", layout="wide")

# 🏷️ Nagłówek
st.title("📈 Finviz Stock Screener")
st.caption("Analiza spółek giełdowych + newsy w czasie rzeczywistym")

# ⚙️ Ustawienia
st.sidebar.header("⚙️ Ustawienia pobierania")
max_companies = st.sidebar.number_input("Ilość spółek do pobrania (0 = wszystkie)", min_value=0, value=0, step=10)
with_filters = st.sidebar.checkbox("Zastosuj filtry (Mid Cap, NASDAQ, Rel Volume > 1.5 itd.)", value=True)
get_only_tickers = st.sidebar.checkbox("Tylko tickery?", value=False)

st.markdown("---")

# 📊 Sekcja statystyk
st.subheader("📊 Dane statystyczne spółek")

if st.button("🔎 Pobierz dane o spółkach (statystyki)"):
    with st.spinner("⏳ Pobieranie danych..."):
        df = fetch_finviz(max_companies=max_companies, with_filters=with_filters, get_only_tickers=get_only_tickers)

    st.success(f"Pobrano **{len(df)}** spółek ✅")

    # Podgląd tabeli
    with st.expander("🔍 Podgląd danych", expanded=True):
        st.dataframe(df, use_container_width=True)

    # Zapis CSV
    save_stocks_csv(df, get_only_tickers=get_only_tickers, with_filters=with_filters)
    st.info("📁 Dane zapisane do folderu `data` jako CSV")

    # Pobieranie pliku
    today = datetime.now().strftime("%Y%m%d")
    if get_only_tickers and not with_filters:
        filename = f"finviz_tickers_{today}.csv"
    elif not get_only_tickers and not with_filters:
        filename = f"finviz_stocks_{today}.csv"
    else:
        filename = f"finviz_filtered_stocks_{today}.csv"

    with open(f"data/{filename}", "rb") as f:
        st.download_button("⬇️ Pobierz CSV", data=f, file_name=filename, mime="text/csv")


# 📰 Sekcja newsów
st.subheader("📰 Newsy giełdowe")

if st.button("📰 Pobierz dane o spółkach + newsy"):
    with st.spinner(" (1) ⏳ Pobieram listę spółek..."):
        df_tickers = fetch_finviz(max_companies=max_companies, with_filters=with_filters, get_only_tickers=True)

    tickers = df_tickers["Ticker"].dropna().unique().tolist()

    with st.spinner(" (2) 📰 Pobieram newsy..."):
        all_news = []
        for t in tickers:
            df_news = fetch_google_news_rss(t)
            if not df_news.empty:
                all_news.append(df_news)

        news = pd.concat(all_news, ignore_index=True) if all_news else pd.DataFrame()

    if not news.empty:
        news = add_sentiment(news)
        st.success(f"Pobrano **{len(news)}** newsów dla **{len(tickers)}** spółek ✅")

        # Statystyki
        avg_sentiment = news["sentiment"].mean()
        col1, col2 = st.columns(2)
        col1.metric("📰 Liczba newsów", len(news))
        col2.metric("📊 Średni sentyment", f"{avg_sentiment:.2f}")

        # Podgląd
        with st.expander("🔍 Podgląd newsów", expanded=True):
            st.dataframe(news, use_container_width=True)

        # Zapis
        save_news_csv(news)
        st.info("📁 Newsy zapisane do folderu `data/news` jako CSV")
    else:
        st.warning("⚠️ Brak newsów do wyświetlenia")
