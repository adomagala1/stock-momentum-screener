# web.py
import streamlit as st
import pandas as pd
from datetime import datetime
from stocks import fetch_finviz
from save_data import save_stocks_to_csv, save_news_to_csv
from news import fetch_google_news_rss, add_sentiment
import time
import plotly.express as px

# 🔧 Konfiguracja strony
st.set_page_config(page_title="Finviz Screener", layout="wide", page_icon="📊")

# 🌈 Custom CSS
st.markdown("""
<style>
/* News cards */
.news-card {background: var(--background-color-secondary); border-radius:14px; padding:14px; margin-bottom:12px; box-shadow:0 6px 18px rgba(0,0,0,0.1); animation: slideUp 0.5s ease; color: var(--text-color);}
@keyframes slideUp {from {opacity:0; transform:translateY(10px);} to {opacity:1; transform:translateY(0);}}
.positive {border-left:6px solid #4caf50;}
.neutral {border-left:6px solid #9e9e9e;}
.negative {border-left:6px solid #f44336;}

/* Loader pulse */
.pulse {width:18px; height:18px; border-radius:50%; background:#4facfe; animation:pulseAnim 1.2s infinite; margin:auto;}
@keyframes pulseAnim {0% { transform: scale(0.9); opacity:0.7;} 50% { transform: scale(1.1); opacity:1;} 100% { transform: scale(0.9); opacity:0.7;}}
</style>
""", unsafe_allow_html=True)

# 🏷️ Tytuł
st.title("📊 Finviz Stock Screener + Newsy")
st.caption("Dashboard do pobierania danych giełdowych i newsów — wszystko w jednym miejscu")

# ==============================
# Kontrolki główne
# ==============================
st.markdown("### ⚙️ Ustawienia")
col1, col2, col3 = st.columns(3)
with col1:
    max_companies = st.number_input("Ilość spółek (0 = wszystkie)", min_value=0, value=20, step=10)
with col2:
    with_filters = st.checkbox("Filtry (Mid Cap, NASDAQ, Rel Volume > 1.5)", value=False)
with col3:
    get_only_tickers = st.checkbox("Tylko tickery?", value=False)

# ==============================
# Sekcja 1: Dane giełdowe
# ==============================
st.markdown("### 📈 Dane giełdowe")
if st.button("Pobierz dane giełdowe"):
    with st.spinner("⏳ Pobieram dane ze screenera..."):
        df = fetch_finviz(max_companies=max_companies, with_filters=with_filters, get_only_tickers=get_only_tickers)

    if not df.empty:
        st.success(f"Pobrano {len(df)} spółek")
        st.dataframe(df, use_container_width=True)
        save_stocks_to_csv(df, get_only_tickers=get_only_tickers, with_filters=with_filters)

        today = datetime.now().strftime("%Y%m%d")
        if get_only_tickers and not with_filters:
            filename = f"finviz_tickers_{today}.csv"
        elif not get_only_tickers and not with_filters:
            filename = f"finviz_stocks_{today}.csv"
        else:
            filename = f"finviz_filtered_stocks_{today}.csv"

        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button("Pobierz CSV", csv_data, file_name=filename, mime="text/csv")
    else:
        st.warning("Nie udało się pobrać danych.")

# ==============================
# Sekcja 2: Newsy
# ==============================
st.markdown("### 📰 Newsy")

# --- Wyszukiwanie pojedynczego tickera ---
st.markdown("#### 🔍 Sprawdź konkretny ticker")
search_ticker = st.text_input("Wpisz ticker (np. AAPL, TSLA):").upper()
if st.button("Pobierz newsy dla tego tickera", key="search_ticker_btn"):
    if search_ticker:
        with st.spinner(f"Pobieram newsy dla {search_ticker}..."):
            df_news = fetch_google_news_rss(search_ticker)
            if not df_news.empty:
                df_news = add_sentiment(df_news)
                st.success(f"Pobrano {len(df_news)} newsów dla {search_ticker}")

                avg_sent = df_news['sentiment'].mean()
                col1, col2 = st.columns(2)
                col1.metric("Średni sentyment", f"{avg_sent:.2f}")
                col2.metric("Liczba newsów", len(df_news))

                fig_hist = px.histogram(df_news, x="sentiment", nbins=20, title=f"Histogram sentymentu dla {search_ticker}")
                st.plotly_chart(fig_hist, use_container_width=True)

                st.markdown("### Top 10 newsów")
                for _, row in df_news.head(10).iterrows():
                    sentiment_class = "neutral"
                    if row["sentiment"] > 0.05:
                        sentiment_class = "positive"
                    elif row["sentiment"] < -0.05:
                        sentiment_class = "negative"
                    st.markdown(f"""
                        <div class="news-card {sentiment_class}">
                            <b>[{search_ticker}]</b> {row['headline']}<br>
                            <small>{row.get('published','?')} | {row.get('source','?')}</small><br>
                            <a href="{row['link']}" target="_blank">Czytaj więcej</a>
                        </div>
                        """, unsafe_allow_html=True)

                csv_data = df_news.to_csv(index=False).encode('utf-8')
                st.download_button("Pobierz CSV newsów", csv_data, file_name=f"{search_ticker}_news.csv", mime="text/csv")
            else:
                st.warning(f"Brak newsów dla {search_ticker}")
    else:
        st.warning("Wpisz poprawny ticker.")

st.markdown("---")

# --- Pobranie newsów dla listy tickers ---
st.markdown("#### 📰 Newsy dla listy tickers")
if st.button("Pobierz newsy dla listy tickers", key="all_tickers_btn"):
    with st.spinner("⏳ Pobieram tickery i newsy..."):
        df_tickers = fetch_finviz(max_companies=max_companies, with_filters=False, get_only_tickers=True)

    if "Ticker" not in df_tickers.columns:
        st.error("Błąd: brak kolumny 'Ticker'")
    else:
        tickers = df_tickers["Ticker"].dropna().unique().tolist()
        all_news = []

        # Placeholder do dynamicznego statusu i loadera
        status_placeholder = st.empty()
        loader_placeholder = st.empty()
        progress_bar = st.progress(0)

        for i, t in enumerate(tickers, start=1):
            loader_placeholder.markdown('<div class="pulse"></div>', unsafe_allow_html=True)
            status_placeholder.markdown(f"⏳ Pobieram newsy dla **{t}** ({i}/{len(tickers)})")

            df_news = fetch_google_news_rss(t)
            if not df_news.empty:
                df_news = add_sentiment(df_news)
                all_news.append(df_news)
            progress_bar.progress(i / len(tickers))
            time.sleep(0.15)

        # Usuń loader i status po zakończeniu
        loader_placeholder.empty()
        status_placeholder.empty()
        progress_bar.empty()

        if all_news:
            news = pd.concat(all_news, ignore_index=True)
            st.success(f"Pobrano {len(news)} newsów dla {len(tickers)} spółek")

            avg_sent = news['sentiment'].mean()
            col1, col2, col3 = st.columns(3)
            col1.metric("Średni sentyment", f"{avg_sent:.2f}")
            col2.metric("Liczba newsów", len(news))
            col3.metric("Liczba spółek", len(tickers))

            bins = pd.cut(news['sentiment'], [-1, -0.05, 0.05, 1], labels=["Negatywny", "Neutralny", "Pozytywny"])
            pie_df = bins.value_counts().reset_index()
            pie_df.columns = ["Sentyment", "Liczba"]
            fig_pie = px.pie(pie_df, values="Liczba", names="Sentyment", hole=0.4,
                             color="Sentyment", color_discrete_map={"Pozytywny": "#4caf50", "Neutralny": "#9e9e9e",
                                                                    "Negatywny": "#f44336"})
            st.plotly_chart(fig_pie, use_container_width=True)

            st.subheader("Top 10 newsów")
            for _, row in news.head(10).iterrows():
                sentiment_class = "neutral"
                if row["sentiment"] > 0.05:
                    sentiment_class = "positive"
                elif row["sentiment"] < -0.05:
                    sentiment_class = "negative"
                st.markdown(f"""
                    <div class="news-card {sentiment_class}">
                        <b>[{row['ticker']}]</b> {row['headline']}<br>
                        <small>{row.get('published', '?')} | {row.get('source', '?')}</small><br>
                        <a href="{row['link']}" target="_blank">Czytaj więcej</a>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.warning("Brak newsów.")
