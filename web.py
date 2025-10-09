import sys
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from pymongo.uri_parser import parse_uri

# Dodawanie ścieżki do folderu nadrzędnego, aby importy działały poprawnie
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.stocks import fetch_finviz
from app.news import fetch_google_news_rss, add_sentiment
from app.predictive_model import load_all_stocks_data, get_avg_sentiment_for_tickers
from app.web.auth import login, logout, register, check_login
from app.web.watchlist import get_watchlist, add_to_watchlist, remove_from_watchlist
from app.web.alerts import get_alerts, add_alert, remove_alert, ALERTS_CSS, render_styled_alert_card
from app.db.user_supabase_manager import clean_and_transform_for_db, SupabaseHandler
from app.db.user_mongodb_manager import MongoNewsHandler

# --- Konfiguracja strony ---
st.set_page_config(page_title="Stock AI Dashboard", layout="wide", page_icon="📈")

# --- Inicjalizacja stanu sesji ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_guest" not in st.session_state:
    st.session_state.is_guest = False
if "db_configured" not in st.session_state:
    st.session_state.db_configured = False
if "mongo_configured" not in st.session_state:
    st.session_state.mongo_configured = False

if "sb_url" not in st.session_state or not st.session_state["sb_url"]:
    try:
        st.session_state["sb_url"] = st.secrets["supabase"]["url"]
        st.session_state["sb_api"] = st.secrets["supabase"]["api_key"]
        st.session_state["db_configured"] = True
    except KeyError:
        st.session_state["db_configured"] = False

if "mongo_uri" not in st.session_state or not st.session_state["mongo_uri"]:
    try:
        st.session_state["mongo_uri"] = st.secrets["mongodb"]["uri"]
        st.session_state["mongo_db"] = st.secrets["mongodb"]["database"]
        st.session_state["mongo_configured"] = True
    except KeyError:
        st.session_state["mongo_configured"] = False

# --- Funkcje pomocnicze i UI ---

def apply_custom_css():
    """Aplikuje niestandardowe style CSS dla całej aplikacji."""
    st.markdown("""
        <style>
            .stButton>button { border-radius: 8px; }
            h1, h2, h3 { color: #0d1b2a; }
            .stTabs [data-baseweb="tab-list"] { gap: 24px; }
            .news-card {
                background-color: #ffffff; border-radius: 10px; padding: 16px;
                margin-bottom: 12px; border: 1px solid #e6e6e6;
                box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
            }
            .news-card:hover { transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,0.08); }
            .news-title a { text-decoration: none; color: #1e3a8a !important; font-weight: 600; font-size: 1.1em; }
            .news-title a:hover { text-decoration: underline; }
            .news-meta { font-size: 0.85em; color: #6c757d; margin-top: 8px; }
            .sentiment-badge { 
                display: inline-block; padding: 3px 10px; border-radius: 15px; 
                font-weight: 500; color: white; font-size: 0.8em; 
            }
            .positive-bg { background-color: #28a745; }
            .negative-bg { background-color: #dc3545; }
            .neutral-bg { background-color: #6c757d; }
        </style>
    """, unsafe_allow_html=True)
    st.markdown(ALERTS_CSS, unsafe_allow_html=True)


def render_db_status_indicator(db_name: str, is_configured: bool):
    """Renderuje wskaźnik statusu połączenia."""
    if is_configured:
        st.markdown(f"**{db_name}:** <span style='color:green;'>✅ Połączono</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"**{db_name}:** <span style='color:red;'>❌ Brak Połączenia</span>", unsafe_allow_html=True)


def render_guest_lock_ui(title: str, icon: str, description: str):
    """Wyświetla blokadę funkcji dla gości."""
    with st.container(border=True):
        st.markdown(f"### {icon} {title}")
        st.markdown(description)
        st.divider()
        if st.button("Zarejestruj się lub zaloguj, aby odblokować", type="primary", key=f"lock_{title}",
                     use_container_width=True):
            logout()
            st.rerun()


# --- GŁÓWNE STRONY I KOMPONENTY ---

def render_login_page():
    """Renderuje stronę logowania, rejestracji i wejścia jako gość."""
    _, col_main, _ = st.columns([1, 1.5, 1])
    with col_main:
        st.markdown("<h1 style='text-align: center; color: #0d1b2a;'>📈 AI Stock Screener</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Zaloguj się, zarejestruj lub kontynuuj jako gość.</p>",
                    unsafe_allow_html=True)
        login_tab, register_tab, guest_tab = st.tabs(["**Logowanie**", "**Rejestracja**", "**Tryb Gościa**"])
        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="user@example.com")
                password = st.text_input("Hasło", type="password", placeholder="••••••••")
                if st.form_submit_button("Zaloguj się", use_container_width=True, type="primary"):
                    if login(email, password):
                        st.session_state.is_guest = False
                        st.rerun()
        with register_tab:
            with st.form("register_form"):
                email = st.text_input("Email", placeholder="user@example.com")
                password = st.text_input("Hasło", type="password", placeholder="••••••••")
                if st.form_submit_button("Zarejestruj się", use_container_width=True):
                    register(email, password)
        with guest_tab:
            st.info(
                "Tryb gościa pozwala na przeglądanie danych i testowanie modelu. Personalizacja wymaga zalogowania.",
                icon="ℹ️")
            if st.button("Kontynuuj jako Gość", use_container_width=True):
                st.session_state.user = {"email": "Gość", "id": None}
                st.session_state.is_guest = True
                st.toast("✅ Uruchomiono tryb gościa.", icon="👋")
                st.rerun()


def render_dashboard():
    """Renderuje główny dashboard z zakładkami."""
    user, is_guest = st.session_state.user, st.session_state.is_guest
    col_title, col_user = st.columns([0.7, 0.3])
    with col_title:
        st.title("📈 AI Stock Screener")
    with col_user:
        st.markdown("<div style='text-align: right; padding-top: 10px;'>", unsafe_allow_html=True)
        if is_guest:
            if st.button("Zaloguj / Zarejestruj się", use_container_width=True, type="primary"): logout(); st.rerun()
        else:
            user_email = getattr(user, 'email', 'Nieznany')
            st.markdown(f"Zalogowano jako: **{user_email}**")
            if st.button("Wyloguj", use_container_width=True): logout(); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.divider()

    with st.expander("⚙️ Konfiguracja Połączenia z Bazami Danych"):
        with st.container(border=True):
            col1, col2 = st.columns(2)
            with col1: render_db_status_indicator("Supabase (Dane Użytkowników)", st.session_state.get("db_configured"))
            with col2: render_db_status_indicator("MongoDB (Newsy)", st.session_state.get("mongo_configured"))

        # --- Konfiguracja Supabase (bez zmian) ---
        st.markdown("##### Supabase (Główna baza)")
        sb_url_input = st.text_input("Supabase URL", value=st.session_state.get("sb_url", ""),
                                     placeholder="https:// TwojeID .supabase.co")
        sb_api_input = st.text_input("Supabase API Key (anon key)", type="password",
                                     value=st.session_state.get("sb_api", ""))
        if st.button("💾 Połącz z Supabase", key="connect_supabase", use_container_width=True):
            if sb_url_input and sb_api_input:
                st.session_state.update({"sb_url": sb_url_input, "sb_api": sb_api_input, "db_configured": True})
                st.success("Konfiguracja Supabase zapisana.")
                st.rerun()
            else:
                st.error("Wypełnij URL i klucz API dla Supabase.")
        st.markdown("---")

        # --- Elastyczna Konfiguracja MongoDB ---
        st.markdown("##### MongoDB (Archiwum newsów)")
        mongo_mode = st.radio("Sposób konfiguracji MongoDB:",
                              ("Użyj Connection String (zalecane)", "Wprowadź dane oddzielnie"), horizontal=True,
                              key="mongo_config_mode")

        # Łączenie z MongoDB
        if mongo_mode == "Użyj Connection String (zalecane)":
            mongo_uri = st.text_input("MongoDB Connection String (URI)", value=st.session_state.get("mongo_uri", ""))
            if st.button("💾 Połącz z MongoDB", key="connect_mongo_uri", use_container_width=True):
                if mongo_uri:
                    try:
                        db_name = parse_uri(mongo_uri).get('database')
                        if not db_name:
                            st.error("URI musi zawierać nazwę bazy danych (np. .../mojaBaza?...)")
                        else:
                            st.session_state.update(
                                {"mongo_uri": mongo_uri, "mongo_db": db_name, "mongo_configured": True})
                            st.success(f"Konfiguracja MongoDB zapisana. Baza: '{db_name}'")
                            st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Nieprawidłowy format URI: {e}")
                else:
                    st.error("Wklej pełny Connection String dla MongoDB.")
        else:
            mongo_uri_sep = st.text_input("Mongo URI", value=st.session_state.get("mongo_uri", ""), key="mongo_uri_sep")
            mongo_db_name_sep = st.text_input("Nazwa bazy", value=st.session_state.get("mongo_db", ""),
                                              key="mongo_db_sep")
            if st.button("💾 Połącz z MongoDB", key="connect_mongo_sep", use_container_width=True):
                if mongo_uri_sep and mongo_db_name_sep:
                    st.session_state.update(
                        {"mongo_uri": mongo_uri_sep, "mongo_db": mongo_db_name_sep, "mongo_configured": True})
                    st.success(f"Konfiguracja MongoDB zapisana. Baza: '{mongo_db_name_sep}'")
                    st.experimental_rerun()
                else:
                    st.error("Wypełnij oba pola: URI i nazwę bazy.")

        if st.session_state.get("db_configured") or st.session_state.get("mongo_configured"):
            if st.button("❌ Rozłącz wszystkie bazy", use_container_width=True, type="secondary"):
                st.session_state.update(
                    {"db_configured": False, "sb_url": "", "sb_api": "", "mongo_configured": False, "mongo_uri": "",
                     "mongo_db": ""})
                st.rerun()

    user_id = getattr(user, 'id', None)
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📈 **Dane giełdowe**", "📰 **Newsy i Sentyment**", "🤖 **Model Predykcyjny**", "❤️ **Watchlista**",
         "🔔 **Alerty Cenowe**"])
    display_stocks_tab(tab1)
    display_news_tab(tab2, user_id, is_guest)
    display_model_tab(tab3)
    display_watchlist_tab(tab4, user_id, is_guest)
    display_alerts_tab(tab5, user_id, is_guest)


# --- Funkcje renderujące poszczególne zakładki ---
# (Reszta kodu od `display_news_cards` w dół pozostaje BEZ ZMIAN)
def display_news_cards(df):
    """Wyświetla newsy w formie estetycznych kart."""
    for _, row in df.iterrows():
        sentiment_score = row['sentiment']
        if sentiment_score > 0.05:
            sentiment_label, sentiment_class = "Pozytywny", "positive-bg"
        elif sentiment_score < -0.05:
            sentiment_label, sentiment_class = "Negatywny", "negative-bg"
        else:
            sentiment_label, sentiment_class = "Neutralny", "neutral-bg"
        st.markdown(f"""
            <div class="news-card">
                <p class="news-title"><a href="{row['link']}" target="_blank">{row['title']}</a></p>
                <p class="news-meta">Opublikowano: {row['published']} | Sentyment: <span class="sentiment-badge {sentiment_class}">{sentiment_label} ({sentiment_score:.2f})</span></p>
            </div>
        """, unsafe_allow_html=True)


def display_stocks_tab(tab_container):
    with tab_container:
        st.subheader("Pobierz dane giełdowe z Finviz")
        with st.form("finviz_form"):
            col1, col2, col3 = st.columns(3)
            max_companies = col1.number_input("Maksymalna ilość spółek (0 = wszystkie)", min_value=0, value=50, step=10)
            get_only_tickers = col2.checkbox("Tylko tickery", value=False)
            with_filters = col3.checkbox("Filtry", value=False)
            if st.form_submit_button("🔄 Pobierz dane giełdowe", type="primary", use_container_width=True):
                with st.spinner("Pobieram dane z Finviz..."):
                    try:
                        df = fetch_finviz(max_companies=max_companies, get_only_tickers=get_only_tickers,
                                          with_filters=with_filters)
                        st.session_state["latest_df"] = df
                    except Exception as e:
                        st.error(f"Nie udało się pobrać danych: {e}")
                        st.session_state["latest_df"] = pd.DataFrame()
        if "latest_df" in st.session_state and not st.session_state.latest_df.empty:
            df = st.session_state.latest_df
            st.success(f"Pobrano dane dla {len(df)} spółek.")
            st.dataframe(df)
            if not st.session_state.get("db_configured"):
                st.warning("Skonfiguruj połączenie z Supabase, aby zapisać dane.")
                st.button("💾 Zapisz do Supabase", use_container_width=True, disabled=True)
            else:
                if st.button("💾 Zapisz do Supabase", use_container_width=True):
                    with st.spinner("Przygotowuję i zapisuję dane..."):
                        sb_handler = SupabaseHandler(st.session_state["sb_url"], st.session_state["sb_api"])
                        df_cleaned = clean_and_transform_for_db(df)
                        saved_count = sb_handler.save_dataframe(df_cleaned)
                        if saved_count > 0:
                            st.success(f"✅ Zapisano {saved_count} rekordów!")
                        else:
                            st.error("❌ Zapis nie powiódł się. Sprawdź logi lub konfigurację bazy.")


def display_news_tab(tab_container, user_id, is_guest):
    with tab_container:
        st.subheader("Analiza sentymentu na podstawie newsów")
        ticker = None
        if not is_guest and st.session_state.get("db_configured"):
            watchlist = get_watchlist(user_id) if user_id else []
            watchlist_tickers = [item['ticker'] for item in watchlist] if watchlist else []
            options = [""] + watchlist_tickers
            col1, col2 = st.columns(2)
            ticker_from_list = col1.selectbox("Wybierz spółkę z Twojej watchlisty:", options=options,
                                              label_visibility="collapsed")
            ticker_manual = col2.text_input("...lub wpisz ticker ręcznie:", key="news_ticker_user",
                                            label_visibility="collapsed",
                                            placeholder="...lub wpisz ticker ręcznie").upper()
            ticker = ticker_manual or ticker_from_list
        else:
            ticker = st.text_input("🔎 Wpisz ticker (np. AAPL, TSLA)", key="news_ticker_guest").upper()
        if st.button("📥 Pobierz i analizuj newsy", type="primary", use_container_width=True):
            if ticker:
                with st.spinner(f"Analizuję newsy dla {ticker}..."):
                    df_news = fetch_google_news_rss(ticker)
                    if not df_news.empty:
                        df_news_sentiment = add_sentiment(df_news)
                        st.markdown(f"#### Wyniki dla: **{ticker}**")
                        cols = st.columns(2)
                        cols[0].metric("Średni sentyment", f"{df_news_sentiment['sentiment'].mean():.3f}")
                        cols[1].metric("Liczba newsów", len(df_news_sentiment))
                        fig = px.histogram(df_news_sentiment, x="sentiment", nbins=20,
                                           title=f"Rozkład sentymentu dla {ticker}")
                        st.plotly_chart(fig, use_container_width=True)
                        display_news_cards(df_news_sentiment)
                    else:
                        st.warning(f"Nie znaleziono nowszych wiadomości dla tickera {ticker}.")
            else:
                st.warning("Proszę wpisać lub wybrać ticker do analizy.")


def display_model_tab(tab_container):
    with tab_container:
        st.subheader("Model predykcyjny AI")
        st.info("Model ocenia spółki na podstawie ceny, kapitalizacji i sentymentu. Wymaga danych z bazy Supabase.",
                icon="💡")
        top_n = st.slider("📊 Ile najlepszych spółek wyświetlić?", 5, 50, 20, 5)
        if not st.session_state.get("db_configured"):
            st.warning("Model predykcyjny wymaga połączenia z bazą Supabase. Proszę skonfigurować połączenie.",
                       icon="⚠️")
            st.button("🚀 Uruchom model", type="primary", use_container_width=True, disabled=True)
        else:
            if st.button("🚀 Uruchom model", type="primary", use_container_width=True):
                with st.spinner("Analizuję dane i uruchamiam model..."):
                    df_all = load_all_stocks_data()
                    if not df_all.empty:
                        tickers = df_all['ticker'].dropna().unique()
                        dates = df_all['import_date'].dropna().unique()
                        all_sentiments = [get_avg_sentiment_for_tickers(tickers, day) for day in dates]
                        sentiment_all = pd.concat(all_sentiments, ignore_index=True)
                        df_all = df_all.merge(sentiment_all, on=['ticker', 'import_date'], how='left').fillna(
                            {'avg_sentiment': 0.0})
                        df_all['market_cap_log'] = np.log1p(df_all['market_cap'].astype(float))
                        p_norm = (df_all['price'] - df_all['price'].min()) / (
                                    df_all['price'].max() - df_all['price'].min())
                        mc_norm = (df_all['market_cap_log'] - df_all['market_cap_log'].min()) / (
                                    df_all['market_cap_log'].max() - df_all['market_cap_log'].min())
                        sentiment_norm = (df_all['avg_sentiment'] - df_all['avg_sentiment'].min()) / (
                                    df_all['avg_sentiment'].max() - df_all['avg_sentiment'].min())
                        df_all['potential_score'] = (0.5 * p_norm + 0.3 * mc_norm + 0.2 * sentiment_norm) * 100
                        df_all_sorted = df_all.sort_values(by='potential_score', ascending=False).head(top_n)
                        st.dataframe(
                            df_all_sorted[['ticker', 'price', 'market_cap', 'avg_sentiment', 'potential_score']])
                        st.success("✅ Model zakończył pracę.")
                    else:
                        st.warning(
                            "Brak danych w bazie do analizy. Pobierz i zapisz dane giełdowe w pierwszej zakładce.")


def display_watchlist_tab(tab_container, user_id, is_guest):
    with tab_container:
        if is_guest:
            render_guest_lock_ui("Watchlista", "❤️",
                                 "Zapisuj interesujące Cię spółki i miej je zawsze pod ręką. Ta funkcja wymaga konta użytkownika.")
            return

        if not st.session_state.get("db_configured"):
            st.warning("Watchlista wymaga połączenia z bazą danych.", icon="⚠️")
            return

        st.subheader("Twoja Watchlista")
        with st.form("add_watchlist_form", clear_on_submit=True):
            col1, col2 = st.columns([3, 1])
            ticker_input = col1.text_input("Dodaj spółkę do watchlisty", placeholder="np. AAPL")
            if col2.form_submit_button("➕ Dodaj", type="primary", use_container_width=True):
                if ticker_input:
                    add_to_watchlist(user_id, ticker_input.upper())
                    st.toast(f"Dodano {ticker_input.upper()}")
                    st.experimental_rerun()

        watchlist = get_watchlist(user_id)
        if watchlist:
            df_watchlist = pd.DataFrame(watchlist)[['ticker', 'created_at']]
            st.dataframe(df_watchlist, use_container_width=True, hide_index=True)
            ticker_to_remove = st.selectbox("Wybierz ticker do usunięcia", options=[w['ticker'] for w in watchlist])
            if st.button(f"❌ Usuń {ticker_to_remove}", use_container_width=True):
                remove_from_watchlist(user_id, ticker_to_remove)
                st.toast(f"Usunięto {ticker_to_remove}")
                st.experimental_rerun()
        else:
            st.info("Twoja watchlista jest pusta.")


def display_alerts_tab(tab_container, user_id, is_guest):
    with tab_container:
        if is_guest:
            render_guest_lock_ui("Alerty Cenowe", "🔔",
                                 "Ustawiaj powiadomienia cenowe i nie przegap żadnej okazji. Wymaga konta użytkownika.")
            return

        if not st.session_state.get("db_configured"):
            st.warning("Alerty cenowe wymagają połączenia z bazą danych.", icon="⚠️")
            return

        st.subheader("Twoje Alerty Cenowe")
        with st.expander("➕ Dodaj nowy alert"):
            with st.form("add_alert_form", clear_on_submit=True):
                col1, col2, col3 = st.columns(3)
                ticker_input = col1.text_input("Ticker", placeholder="np. TSLA")
                target_price = col2.number_input("Cena docelowa", min_value=0.01, value=100.0, step=0.01, format="%.2f")
                condition = col3.radio("Warunek", ["Powyżej", "Poniżej"], horizontal=True)
                if st.form_submit_button("💾 Dodaj alert", type="primary", use_container_width=True):
                    if ticker_input:
                        add_alert(user_id, ticker_input.upper(), target_price,
                                  "above" if condition == "Powyżej" else "below")
                        st.toast(f"Alert dla {ticker_input.upper()} dodany.")
                        st.experimental_rerun()

        alerts = get_alerts(user_id)
        if alerts:
            st.markdown("##### Aktywne Alerty")
            for alert in alerts:
                render_styled_alert_card(alert, user_id)
        else:
            st.info("Nie masz jeszcze żadnych aktywnych alertów.")



def main():
    apply_custom_css()
    check_login()
    if st.session_state.get('user') is None:
        render_login_page()
    else:
        render_dashboard()


if __name__ == "__main__":
    main()