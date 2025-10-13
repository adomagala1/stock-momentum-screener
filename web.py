import sys
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from pymongo.uri_parser import parse_uri
from sqlalchemy.engine import Engine
from load_demo_data import load_demo_secrets

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.stocks import fetch_finviz
from app.news import fetch_google_news_rss, add_sentiment
from app.predictive_model import load_all_stocks_data
from app.web.auth import login, logout, register, check_login
from app.web.watchlist import get_watchlist, add_to_watchlist, remove_from_watchlist
from app.web.alerts import get_alerts, add_alert, ALERTS_CSS, render_styled_alert_card
from app.db.user_supabase_manager import clean_and_transform_for_db, SupabaseHandler
from app.db.user_mongodb_manager import MongoNewsHandler
from app.helpers import human_readable_market_cap

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


# --- FUNKCJE POMOCNICZE ---
def apply_custom_css():
    """Aplikuje niestandardowe style CSS dla całej aplikacji."""
    st.markdown("""
        <style>
            .stButton>button { border-radius: 8px; }
            h1, h2, h3 { color: #0d1b2a; }
            .stTabs [data-baseweb="tab-list"] { gap: 24px; }
            .news-card { background-color: #ffffff; border-radius: 10px; padding: 16px; margin-bottom: 12px; border: 1px solid #e6e6e6; box-shadow: 0 4px 12px rgba(0,0,0,0.05); transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out; }
            .news-card:hover { transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,0.08); }
            .news-title a { text-decoration: none; color: #1e3a8a !important; font-weight: 600; font-size: 1.1em; }
            .news-title a:hover { text-decoration: underline; }
            .news-meta { font-size: 0.85em; color: #6c757d; margin-top: 8px; }
            .sentiment-badge { display: inline-block; padding: 3px 10px; border-radius: 15px; font-weight: 500; color: white; font-size: 0.8em; }
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
        st.markdown("<h1 style='text-align: center; color: white;'>📈 AI Stock Screener</h1>", unsafe_allow_html=True)
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

    with st.expander("⚙️ Konfiguracja Połączenia z Bazami Danych",
                     expanded=not (st.session_state.db_configured and st.session_state.mongo_configured)):
        st.info("Wprowadź dane dostępowe do swoich baz danych lub załaduj konfigurację demo.", icon="🔑")

        if st.button("🚀 Załaduj konfigurację DEMO", use_container_width=True):
            load_demo_secrets()

        with st.container(border=True):
            col_sb_status, col_mongo_status = st.columns(2)
            with col_sb_status:
                render_db_status_indicator("Supabase", st.session_state.get("db_configured"))
            with col_mongo_status:
                render_db_status_indicator("MongoDB", st.session_state.get("mongo_configured"))

        st.markdown("##### 1. Konfiguracja Supabase (API & Baza Danych)")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Połączenie przez API**")
            sb_url_input = st.text_input("Supabase URL", value=st.session_state.get("sb_url", ""), key="sb_url_ui")
            sb_api_input = st.text_input("Supabase API Key (anon key)", type="password",
                                         value=st.session_state.get("sb_api", ""), key="sb_api_ui")
        with col2:
            st.markdown("**Bezpośrednie Połączenie z Bazą Danych**")
            sb_db_host = st.text_input("Host Bazy Danych", value=st.session_state.get("sb_db_host", ""),
                                       key="sb_db_host_ui")
            sb_db_user = st.text_input("Użytkownik Bazy Danych", value=st.session_state.get("sb_db_user", "postgres"),
                                       key="sb_db_user_ui")
            sb_db_password = st.text_input("Hasło Bazy Danych", type="password",
                                           value=st.session_state.get("sb_db_password", ""), key="sb_db_password_ui")
            sb_db_port = st.number_input("Port Bazy Danych", value=st.session_state.get("sb_db_port", 5432),
                                         key="sb_db_port_ui")
            sb_db_name = st.text_input("Nazwa Bazy Danych", value=st.session_state.get("sb_db_name", "postgres"),
                                       key="sb_db_name_ui")

        if st.button("💾 Zapisz i Połącz z Supabase", key="connect_supabase_unified", use_container_width=True):
            if all([sb_url_input, sb_api_input, sb_db_host, sb_db_user, sb_db_password]):
                st.session_state.update({
                    "sb_url": sb_url_input, "sb_api": sb_api_input,
                    "sb_db_host": sb_db_host, "sb_db_user": sb_db_user,
                    "sb_db_password": sb_db_password, "sb_db_port": sb_db_port,
                    "sb_db_name": sb_db_name, "db_configured": True
                })
                st.success("Konfiguracja Supabase zapisana pomyślnie dla tej sesji.")
                st.rerun()
            else:
                st.error("Wypełnij wszystkie wymagane pola dla Supabase (API i Baza Danych).")
        st.markdown("---")

        st.markdown("##### 2. Konfiguracja MongoDB (Archiwum newsów)")
        mongo_uri = st.text_input("MongoDB Connection String (URI)", value=st.session_state.get("mongo_uri", ""),
                                  placeholder="mongodb+srv://user:pass@cluster.mongodb.net/nazwabazy",
                                  key="mongo_uri_ui")
        if st.button("💾 Połącz z MongoDB", key="connect_mongo_uri", use_container_width=True):
            if mongo_uri:
                try:
                    db_name = parse_uri(mongo_uri).get('database')
                    if not db_name:
                        st.error("URI musi zawierać nazwę bazy danych (np. .../mojaBaza?...)")
                    else:
                        st.session_state.update({"mongo_uri": mongo_uri, "mongo_db": db_name, "mongo_configured": True})
                        st.success(f"Konfiguracja MongoDB zapisana. Połączono z bazą: '{db_name}'")
                        st.rerun()
                except Exception as e:
                    st.error(f"Nieprawidłowy format URI MongoDB: {e}")
            else:
                st.error("Wklej pełny Connection String dla MongoDB.")

    user_id = getattr(user, 'id', None)
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📈 **Dane giełdowe**", "📰 **Newsy i Sentyment**", "🤖 **Model Predykcyjny**", "❤️ **Watchlista**",
         "🔔 **Alerty Cenowe**"])

    # <-- ZMIANA: Każda funkcja wyświetlająca jest teraz w dedykowanym bloku 'with'
    with tab1:
        display_stocks_tab()
    with tab2:
        display_news_section(user_id, is_guest)
    with tab3:
        display_model_tab()
    with tab4:
        display_watchlist_tab(user_id, is_guest)
    with tab5:
        display_alerts_tab(user_id, is_guest)


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


def display_stocks_tab():
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


def display_news_section(user_id, is_guest=False):
    st.subheader("📰 Analiza newsów giełdowych")

    if not st.session_state.get("mongo_configured"):
        st.warning("Analiza newsów wymaga skonfigurowania połączenia z MongoDB.", icon="⚠️")
        return

    mongo_handler = MongoNewsHandler(st.session_state.get("mongo_uri"), st.session_state.get("mongo_db"))

    ticker_options = [""]
    if not is_guest and st.session_state.get("db_configured"):
        watchlist = get_watchlist(user_id)
        if watchlist:
            ticker_options.extend([item['ticker'] for item in watchlist])

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_ticker = st.selectbox("Wybierz spółkę z watchlisty:", options=ticker_options)
    with col2:
        manual_ticker = st.text_input("...lub wpisz ticker ręcznie:", placeholder="np. AAPL").upper()

    # Określ aktywny ticker na podstawie inputów użytkownika
    # Ważne, aby robić to na początku, przed wyświetleniem wyników
    ticker = manual_ticker if manual_ticker else selected_ticker

    if st.button("📥 Pobierz i analizuj newsy", type="primary", use_container_width=True):
        if not ticker:
            st.warning("Wybierz lub wpisz ticker do analizy.")
            return

        with st.spinner(f"Pobieram i analizuję newsy dla {ticker}..."):
            df_news = fetch_google_news_rss(ticker)
            if df_news is None or df_news.empty:
                st.warning(f"Nie znaleziono newsów dla {ticker}.")
                return
            df_news_sentiment = add_sentiment(df_news)
            # Przechowujemy dane w sesji pod kluczem specyficznym dla tickera
            st.session_state[f'news_{ticker}'] = df_news_sentiment
            # Zapisujemy, który ticker jest aktualnie aktywny
            st.session_state['active_news_ticker'] = ticker

    # Sprawdzamy, czy mamy aktywny ticker i dane dla niego w sesji
    active_ticker = st.session_state.get('active_news_ticker')
    if active_ticker and f'news_{active_ticker}' in st.session_state:
        df_to_display = st.session_state[f'news_{active_ticker}']

        st.markdown(f"#### Wyniki dla: **{active_ticker}**")

        col_metric1, col_metric2 = st.columns(2)
        col_metric1.metric("Średni sentyment", f"{df_to_display['sentiment'].mean():.3f}")
        col_metric2.metric("Liczba newsów", len(df_to_display))

        # <-- ZMIANA: Dodajemy przycisk resetowania
        col_save, col_reset = st.columns(2)
        with col_save:
            if st.button("💾 Zapisz do MongoDB", use_container_width=True, key=f"save_{active_ticker}"):
                with st.spinner("Zapisuję newsy do bazy MongoDB..."):
                    records_to_insert = df_to_display.to_dict(orient="records")
                    inserted_count = mongo_handler.insert_news(records_to_insert)
                    st.toast(f"Zapisano {inserted_count} newsów dla {active_ticker} ", icon="😁")
        with col_reset:
            if st.button("🔄 Wyczyść wyniki", use_container_width=True, key=f"reset_{active_ticker}"):
                # Usuwamy dane newsów i informację o aktywnym tickerze z sesji
                if f'news_{active_ticker}' in st.session_state:
                    del st.session_state[f'news_{active_ticker}']
                if 'active_news_ticker' in st.session_state:
                    del st.session_state['active_news_ticker']
                st.rerun() # Odświeżamy stronę, aby zmiany były widoczne

        fig = px.histogram(df_to_display, x="sentiment", nbins=20, title=f"Rozkład sentymentu dla {active_ticker}")
        st.plotly_chart(fig, use_container_width=True)

        display_news_cards(df_to_display)

    st.divider()

    # Reszta funkcji pozostaje bez zmian
    if st.button("🌍 Pobierz newsy dla wszystkich z Supabase", use_container_width=True):
        if not st.session_state.get("db_configured"):
            st.warning("Ta funkcja wymaga połączenia z Supabase.", icon="⚠️")
            return

        with st.spinner("Pobieram tickery z Supabase..."):
            sb_handler = SupabaseHandler(st.session_state["sb_url"], st.session_state["sb_api"])
            tickers_list = sb_handler.get_all_tickers_from_supabase()

        if not tickers_list:
            st.warning("Brak tickerów w Supabase do przetworzenia.")
            return

        st.info(f"Znaleziono {len(tickers_list)} tickerów. Rozpoczynanie pobierania newsow i analizę ich sentymentu")
        progress_bar = st.progress(0, text="Rozpoczete")
        all_news = []
        for i, t in enumerate(tickers_list):
            progress_bar.progress((i + 1) / len(tickers_list), text=f"Przetwarzanie: {t} ({i + 1}/{len(tickers_list)})")
            df_news = fetch_google_news_rss(t)
            if df_news is not None and not df_news.empty:
                df_news_sentiment = add_sentiment(df_news)
                all_news.extend(df_news_sentiment.to_dict(orient="records"))

        if all_news:
            st.success("Pobrano i zapisano wszystkie newsy.")
            mongo_handler.insert_news(all_news)
            st.success("Zapisano wszystkie newsy do bazy MongoDB.")
        else:
            st.info("Nie znaleziono żadnych nowych newsów do zapisania.")


def display_model_tab():
    st.subheader("🤖 Model Predykcyjny AI")
    st.info("Model ocenia spółki na podstawie ceny, kapitalizacji i sentymentu. Wymaga połączenia z Twoimi bazami danych.", icon="💡")
    top_n = st.slider("📊 Ile najlepszych spółek wyświetlić?", 5, 50, 20, 5)

    if not st.session_state.get("db_configured") or not st.session_state.get("mongo_configured"):
        st.warning("Model predykcyjny wymaga skonfigurowania połączenia z Supabase i MongoDB.", icon="⚠️")
        st.button("🚀 Uruchom model", type="primary", use_container_width=True, disabled=True)
        return

    if st.button("🚀 Uruchom model", type="primary", use_container_width=True):
        with st.spinner("Łączenie z bazami i uruchamianie modelu..."):
            sb_handler = SupabaseHandler(st.session_state["sb_url"], st.session_state["sb_api"])
            engine = sb_handler.create_sqlalchemy_engine()
            if not isinstance(engine, Engine):
                st.error("Nie udało się utworzyć połączenia z bazą Supabase. Sprawdź dane w konfiguracji.")
                return

            df_all = load_all_stocks_data()
            if df_all.empty:
                st.warning("Brak danych o spółkach w Twojej bazie. Najpierw pobierz i zapisz dane w zakładce 'Dane giełdowe'.")
                return

            mongo_handler = MongoNewsHandler(st.session_state["mongo_uri"], st.session_state["mongo_db"])
            tickers = df_all['ticker'].dropna().unique().tolist()
            st.info(f"Pobieram sentyment dla {len(tickers)} unikalnych spółek...")

            sentiment_df = mongo_handler.get_average_sentiment_for_tickers(tickers)

            if sentiment_df is None or sentiment_df.empty:
                sentiment_df = pd.DataFrame(columns=['ticker', 'avg_sentiment'])
                st.info("Brak sentymentów w bazie MongoDB. Zapisujesz sentymenty w bazie MongoDB.")

            df_all = df_all.merge(sentiment_df, on='ticker', how='left')
            df_all['avg_sentiment'] = df_all['avg_sentiment'].fillna(0.0)

            df_all['market_cap_log'] = np.log1p(df_all['market_cap'].astype(float))
            p_norm = (df_all['price'] - df_all['price'].min()) / (df_all['price'].max() - df_all['price'].min() + 1e-9)
            mc_norm = (df_all['market_cap_log'] - df_all['market_cap_log'].min()) / (df_all['market_cap_log'].max() - df_all['market_cap_log'].min() + 1e-9)

            if (df_all['avg_sentiment'].max() - df_all['avg_sentiment'].min()) > 0:
                sentiment_norm = (df_all['avg_sentiment'] - df_all['avg_sentiment'].min()) / (df_all['avg_sentiment'].max() - df_all['avg_sentiment'].min())
            else:
                sentiment_norm = 0.0

            # Normalizacja i potencjal_score jak wcześniej
            df_all['potential_score'] = (0.5 * p_norm + 0.3 * mc_norm + 0.2 * sentiment_norm) * 100

            # --> Dodaj agregację po tickerze, aby każdy ticker pojawiał się tylko raz
            df_all['ticker'] = df_all['ticker'].astype(str).str.upper()  # ujednolicenie
            df_unique = df_all.groupby('ticker', as_index=False).agg({
                'company': 'first',  # albo najczęściej występująca nazwa
                'price': 'last',  # cena z ostatniego rekordu
                'market_cap': 'last',  # kapitalizacja z ostatniego rekordu
                'avg_sentiment': 'mean',  # średni sentyment
                'potential_score': 'max'  # najwyższy score
            })

            df_all_sorted = df_unique.sort_values(by='potential_score', ascending=False).head(top_n)
            df_all_sorted['market_cap'] = df_all_sorted['market_cap'].apply(human_readable_market_cap)
            st.dataframe(
                df_all_sorted[['ticker', 'company', 'price', 'market_cap', 'avg_sentiment', 'potential_score']])

            st.success("✅ Model zakończył pracę.")


def display_watchlist_tab(user_id, is_guest): # <-- ZMIANA
    if is_guest:
        render_guest_lock_ui("Watchlista", "❤️", "Zapisuj interesujące Cię spółki i miej je zawsze pod ręką. Ta funkcja wymaga konta użytkownika.")
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
                st.rerun()

    watchlist = get_watchlist(user_id)
    if watchlist:
        df_watchlist = pd.DataFrame(watchlist)[['ticker']]
        st.dataframe(df_watchlist, use_container_width=True, hide_index=True)
        ticker_to_remove = st.selectbox("Wybierz ticker do usunięcia", options=[w['ticker'] for w in watchlist], key="remove_watchlist_select")
        if st.button(f"❌ Usuń {ticker_to_remove}", use_container_width=True, key="remove_watchlist_btn"):
            remove_from_watchlist(user_id, ticker_to_remove)
            st.toast(f"Usunięto {ticker_to_remove}")
            st.rerun()
    else:
        st.info("Twoja watchlista jest pusta.")


def display_alerts_tab(user_id, is_guest): # <-- ZMIANA
    if is_guest:
        render_guest_lock_ui("Alerty Cenowe", "🔔", "Ustawiaj powiadomienia cenowe i nie przegap żadnej okazji. Wymaga konta użytkownika.")
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
                    add_alert(user_id, ticker_input.upper(), target_price, "above" if condition == "Powyżej" else "below")
                    st.toast(f"Alert dla {ticker_input.upper()} dodany.")
                    st.rerun()

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