# web.py
from datetime import datetime
import sys
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo.uri_parser import parse_uri

# --- Importy z projektu ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.stocks import fetch_finviz
from app.news import fetch_google_news_rss, add_sentiment
from app.predictive_model import initialize_clients, process_historical_analysis, analyze_single_ticker, \
    display_top_stocks_card_view
from app.web.auth import login, logout, register, check_login
from app.web.watchlist import get_watchlist, add_to_watchlist, remove_from_watchlist
from app.web.alerts import get_alerts, add_alert, remove_alert, ALERTS_CSS, render_styled_alert_card
from app.db.user_supabase_manager import clean_and_transform_for_db, SupabaseHandler
from app.db.user_mongodb_manager import MongoNewsHandler
from app.load_demo_data import load_demo_secrets
from app.helpers import sql_script_help, filters_help

st.set_page_config(page_title="Stock Playground", layout="wide", page_icon="🛝")

if "user" not in st.session_state:
    st.session_state.user = None
if "is_guest" not in st.session_state:
    st.session_state.is_guest = False
if "db_configured" not in st.session_state:
    st.session_state.db_configured = False
if "mongo_configured" not in st.session_state:
    st.session_state.mongo_configured = False
if "news_data" not in st.session_state:
    st.session_state.news_data = {"ticker": None, "df": pd.DataFrame()}
if "clients_initialized" not in st.session_state:
    st.session_state.clients_initialized = False
if "lock_password" not in st.session_state:
    st.session_state["lock_password"] = True
if "sb_db_password" not in st.session_state:
    st.session_state["sb_db_password"] = ""
if "lock_mongo_uri" not in st.session_state:
    st.session_state["lock_mongo_uri"] = True
if "mongo_uri" not in st.session_state:
    st.session_state["mongo_uri"] = ""

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
    status_color = "green" if is_configured else "red"
    status_icon = "✅" if is_configured else "❌"
    status_text = "Połączono" if is_configured else "Brak Połączenia"
    st.markdown(f"**{db_name}:** <span style='color:{status_color};'>{status_icon} {status_text}</span>",
                unsafe_allow_html=True)


@st.cache_data
def convert_df_to_csv(df: pd.DataFrame):
    return df.to_csv(index=False).encode('utf-8')


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
    _, col_main, _ = st.columns([1, 1.5, 1])
    with col_main:
        st.markdown("<h1 style='text-align: center; color: white;'> AI Stock Playground </h1>", unsafe_allow_html=True)
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
                "Tryb gościa pozwala na pobieranie newsow, danych ALE Personalizacja wymaga zalogowania.",
                icon="ℹ️")
            if st.button("Kontynuuj jako Gość", use_container_width=True):
                st.session_state.user = {"email": "Gość", "id": None}
                st.session_state.is_guest = True
                st.toast("✅ Uruchomiono tryb gościa.", icon="👋")
                st.rerun()


def render_dashboard():
    user, is_guest = st.session_state.user, st.session_state.is_guest
    user_id = getattr(user, 'id', None)

    col_title, col_user = st.columns([0.7, 0.3])
    with col_title:
        st.title("🛝 Stock Playground")
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

    render_config_expander()
    tabs = st.tabs(
        ["📈 **Dane giełdowe**", "📰 **Newsy i Sentyment**", "🤖 **Model Predykcyjny**",
         f"{'💔' if is_guest else '❤️'} **Watchlista**",
         f"{'🔐' if is_guest else '🔔'} **Alerty Cenowe**"])

    with tabs[0]:
        display_stocks_tab()
    with tabs[1]:
        display_news_tab(user_id, is_guest)
    with tabs[2]:
        display_model_tab()
    with tabs[3]:
        display_watchlist_tab(user_id, is_guest)
    with tabs[4]:
        display_alerts_tab(user_id, is_guest)


def render_config_expander():
    with st.expander("⚙️ Konfiguracja Połączeń z Bazami Danych (do Analizy)",
                     expanded=False):
        st.info("Te bazy danych są potrzebne do działania zakładek 'Dane Giełdowe', 'Newsy' i 'Model Predykcyjny'. "
                "Możesz załadować konfigurację demo lub wprowadzić własne dane.", icon="🔑")
        if st.button("🚀 Załaduj konfigurację DEMO", use_container_width=True):
            try:
                load_demo_secrets()
                st.success("Konfiguracja DEMO załadowana.")
                st.rerun()
            except ImportError:
                st.error("Nie znaleziono pliku `load_demo_data.py`")
            except Exception as e:
                st.error(f"Błąd podczas ładowania konfiguracji DEMO: {e}")

        with st.container(border=True):
            col_sb_status, col_mongo_status = st.columns(2)
            with col_sb_status:
                render_db_status_indicator("Supabase (Dane)", st.session_state.get("db_configured"))
            with col_mongo_status:
                render_db_status_indicator("MongoDB (Newsy)", st.session_state.get("mongo_configured"))

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

            display_pass = "" if st.session_state["lock_password"] else st.session_state["sb_db_password"]

            sb_db_password = st.text_input(
                "Hasło do bazy danych",
                value=display_pass,
                type="password",
                key="sb_db_password_ui",
                help="Wpisz hasło do bazy danych (nigdy nie będzie widoczne w czystej formie)."
            )
            if sb_db_password and sb_db_password != "********":
                st.session_state["sb_db_password"] = sb_db_password
                st.session_state["lock_password"] = False

            sb_db_port = st.number_input("Port Bazy Danych", value=st.session_state.get("sb_db_port", 5432),
                                         key="sb_db_port_ui")
            sb_db_name = st.text_input("Nazwa Bazy Danych", value=st.session_state.get("sb_db_name", "postgres"),
                                       key="sb_db_name_ui", help=sql_script_help)

        if st.button("💾 Zapisz i Połącz z Supabase", key="connect_supabase_unified", use_container_width=True):
            if all([sb_url_input, sb_api_input, sb_db_host, sb_db_user, sb_db_password]):
                st.session_state.update(
                    {"sb_url": sb_url_input, "sb_api": sb_api_input, "sb_db_host": sb_db_host, "sb_db_user": sb_db_user,
                     "sb_db_password": sb_db_password, "sb_db_port": sb_db_port, "sb_db_name": sb_db_name,
                     "db_configured": True})
                st.success("Konfiguracja Supabase zapisana pomyślnie. Odświeżam...")
                st.rerun()
            else:
                st.error("Wypełnij wszystkie wymagane pola dla Supabase (API i Baza Danych).")
        st.markdown("---")
        st.markdown("##### 2. Konfiguracja MongoDB (Archiwum newsów)")
        display_mongo_uri = "" if not st.session_state["lock_mongo_uri"] else "********"
        mongo_uri_input = st.text_input(
            "MongoDB Connection String (URI)",
            value=display_mongo_uri,
            type="password",
            key="mongo_uri_ui",
            help="Wklej pełny Connection String dla MongoDB (nigdy nie będzie widoczny w czystej formie)."
        )
        if mongo_uri_input and mongo_uri_input != "********":
            st.session_state["mongo_uri"] = mongo_uri_input
            st.session_state["lock_mongo_uri"] = False

        if st.button("💾 Połącz z MongoDB", key="connect_mongo_uri", use_container_width=True):
            mongo_uri_to_use = st.session_state.get("mongo_uri", "")
            if mongo_uri_to_use:
                try:
                    db_name = parse_uri(mongo_uri_to_use).get('database')
                    if not db_name:
                        st.error("URI musi zawierać nazwę bazy danych")
                    else:
                        st.session_state.update({
                            "mongo_uri": mongo_uri_to_use,
                            "mongo_db": db_name,
                            "mongo_configured": True
                        })
                        st.success(f"Konfiguracja MongoDB zapisana. Połączono z bazą: '{db_name}'. Odświeżam...")
                        st.rerun()
                except Exception as e:
                    st.error(f"Nieprawidłowy format URI MongoDB: {e}")
            else:
                st.error("Wklej pełny Connection String dla MongoDB.")


def display_stocks_tab():
    st.markdown("[🌐 Otwórz Finviz Screener](https://finviz.com/screener.ashx?v=111)", unsafe_allow_html=True)
    with st.form("finviz_form"):
        col1, col2, col3 = st.columns(3)
        max_companies = col1.number_input("Maksymalna ilość spółek (0 = wszystkie)", min_value=0, value=50, step=10)
        get_only_tickers = col2.checkbox("Tylko tickery", value=False)
        with_filters = col3.checkbox("Filtry", value=False, help=filters_help)
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
        st.dataframe(df.head(100))

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Zapisz do Supabase", use_container_width=True,
                         disabled=not st.session_state.get("db_configured")):
                with st.spinner("Przygotowuję i zapisuję dane do Supabase..."):
                    sb_handler = SupabaseHandler(st.session_state["sb_url"], st.session_state["sb_api"])
                    df_cleaned = clean_and_transform_for_db(df)
                    saved_count = sb_handler.save_dataframe(df_cleaned)
                    if saved_count > 0:
                        st.success(f"✅ Zapisano {saved_count} rekordów do Supabase!")
                    else:
                        st.error("❌ Zapis do Supabase nie powiódł się. Sprawdź logi lub konfigurację bazy.")
        with col2:
            csv_data = convert_df_to_csv(df)
            st.download_button(label="📥 Pobierz jako CSV", data=csv_data, file_name="finviz_stocks.csv",
                               mime="text/csv", use_container_width=True)


def display_news_tab(user_id, is_guest=False):
    st.subheader("📰 Analiza newsów giełdowych")

    ticker_options = [""]
    if not is_guest:
        watchlist = get_watchlist(user_id)
        if watchlist:
            ticker_options.extend([item['ticker'] for item in watchlist])

    col1, col2 = st.columns([1, 1])
    with col1:
        selected_ticker = st.selectbox("Wybierz spółkę z watchlisty:", options=ticker_options)
    with col2:
        manual_ticker = st.text_input("wpisz ticker ręcznie:", placeholder="np. AAPL").upper()

    ticker_to_analyze = manual_ticker if manual_ticker else selected_ticker
    how_many_news = st.number_input("Ile newsów dla tej spółki pobrać?", min_value=1, value=10, max_value=100)

    if st.button("📥 Pobierz i analizuj newsy", type="primary", use_container_width=True):
        mongo_handler = None
        if st.session_state.get("mongo_configured"):
            mongo_handler = MongoNewsHandler(st.session_state.get("mongo_uri"), st.session_state.get("mongo_db"))

        if not ticker_to_analyze:
            st.warning("Wybierz lub wpisz ticker do analizy.")
        else:
            with st.spinner(f"Pobieram i analizuję newsy dla {ticker_to_analyze}..."):
                df_news = fetch_google_news_rss(ticker_to_analyze, limit=how_many_news)
                if df_news is None or df_news.empty:
                    st.warning(f"Nie znaleziono newsów dla {ticker_to_analyze}.")
                    st.session_state.news_data = {"ticker": None, "df": pd.DataFrame()}
                else:
                    df_news_sentiment = add_sentiment(df_news)
                    st.session_state.news_data = {"ticker": ticker_to_analyze, "df": df_news_sentiment}
            st.rerun()

    # Wyświetlanie wyników dla pojedynczego tickera
    active_ticker = st.session_state.news_data.get("ticker") if "news_data" in st.session_state else None
    df_to_display = st.session_state.news_data.get("df") if "news_data" in st.session_state else pd.DataFrame()

    if active_ticker and not df_to_display.empty:
        st.markdown(f"#### Wyniki dla: **{active_ticker}**")
        display_news_cards(df_to_display)

    st.divider()

    # Pobieranie newsów dla wszystkich tickers z Supabase
    if st.session_state.get("mongo_configured") and st.session_state.get("db_configured"):
        sb_handler = SupabaseHandler(st.session_state["sb_url"], st.session_state["sb_api"])
        all_tickers_count = len(sb_handler.get_all_tickers_from_supabase())
        news_limit = st.text_input(f"🔢 Limit newsów na spółkę: (Masz ich w Supabase {all_tickers_count})",
                                   key="news_limit", value="10")

        if st.button("🌍 Pobierz newsy dla wszystkich z Supabase", use_container_width=True):
            try:
                limit = int(news_limit)
            except ValueError:
                st.warning("Podaj poprawny limit (liczbę całkowitą).", icon="⚠️")
                st.stop()

            with st.spinner("Pobieram tickery z Supabase..."):
                tickers_list = sb_handler.get_all_tickers_from_supabase()

            if not tickers_list:
                st.warning("Brak tickerów w Supabase do przetworzenia.")
                st.stop()

            st.info("Rozpoczynanie pobierania newsów i analizy sentymentu")
            progress_bar = st.progress(0, text="Rozpoczęto")
            all_news = []
            for i, t in enumerate(tickers_list):
                progress_bar.progress((i + 1) / len(tickers_list),
                                      text=f"Przetwarzanie: {t} ({i + 1}/{len(tickers_list)})")
                df_news = fetch_google_news_rss(t, limit=limit)
                if df_news is not None and not df_news.empty:
                    df_news_sentiment = add_sentiment(df_news)
                    all_news.extend(df_news_sentiment.to_dict(orient="records"))

            if all_news:
                st.button("💾 Zapisz do MongoDB", key="save_mongo", use_container_width=True)
                if st.session_state.get("save_mongo_trigger"):
                    mongo_handler = MongoNewsHandler(st.session_state.get("mongo_uri"),
                                                     st.session_state.get("mongo_db"))
                    mongo_handler.insert_news(all_news)
                    st.success(f"Zapisano {len(all_news)} newsów do MongoDB.")
            else:
                st.warning("Brak newsów do zapisania.")
    else:
        st.info("Funkcja zapisania do bazy danych wymaga połączenia z nią, niesamowite ", icon="😑️")


def display_model_tab():
    st.header("Model Predykcyjny ᴮᴱᵀᴬ", divider="gray")
    st.info("Ta funkcja jest w fazie testów (beta). Wyniki mogą być niedokładne, i pewnie takie są")

    if not (st.session_state.get("db_configured") and st.session_state.get("mongo_configured")):
        st.info("Model predykcyjny wymaga dwóch baz danych bo analizuje historyczne wyniki!")
        return

    try:
        supabase_client, news_collection = initialize_clients(
            supabase_url=st.session_state["sb_url"],
            supabase_key=st.session_state["sb_api"],
            mongo_uri=st.session_state["mongo_uri"],
            mongo_db_name=st.session_state["mongo_db"]
        )
    except Exception as e:
        st.error(f"Nie udało się połączyć z bazami danych do analizy. Sprawdź konfigurację. Błąd: {e}")
        return

    display_top_stocks_card_view()
    st.divider()

    st.header("Ranking Potencjału Wzrostu (Analiza Historyczna)", anchor=False)
    with st.spinner("Przetwarzam dane historyczne..."):
        result_df = process_historical_analysis(supabase_client, news_collection)

    if not result_df.empty:
        st.dataframe(result_df, use_container_width=True)
    else:
        st.info("Brak wystarczających danych do wygenerowania rankingu.")

    st.divider()
    st.header("Analiza 'Na Żywo' dla Dowolnego Tickera", anchor=False)
    default_ticker = result_df["ticker"].iloc[0] if not result_df.empty else "AAPL"
    ticker_input = st.text_input("Wpisz ticker do analizy:", value=default_ticker).upper()
    if st.button("🚀 Analizuj Ticker", use_container_width=True):
        if ticker_input:
            with st.container(border=True):
                analysis = analyze_single_ticker(ticker_input, supabase_client, news_collection)
                if not analysis.empty:
                    st.dataframe(analysis, use_container_width=True)
        else:
            st.warning("Proszę wpisać ticker.")


def display_watchlist_tab(user_id, is_guest):
    if is_guest:
        render_guest_lock_ui("Watchlista", "💔", "Zapisuj interesujące Cię spółki i miej je zawsze pod ręką.")
        return

    st.subheader("Twoja Watchlista")
    with st.form("add_watchlist_form", clear_on_submit=True):
        col1, col2 = st.columns([3, 1])
        ticker_input = col1.text_input("Dodaj spółkę do watchlisty", placeholder="np. AAPL")

        submit_btn = col2.form_submit_button("➕ Dodaj", type="primary", use_container_width=True)

        if submit_btn:
            if not ticker_input:
                st.warning("Wpisz ticker spółki!")
            elif len(ticker_input) > 20:
                st.warning("Maksymalnie 20 znaków!")
            else:
                add_to_watchlist(user_id, ticker_input.upper())
                st.success(f"Dodano {ticker_input.upper()} do watchlisty ✅")
                st.rerun()

    watchlist = get_watchlist(user_id)
    if watchlist:
        st.markdown("---")
        for item in watchlist:
            col_ticker, col_btn = st.columns([1, 0.2])
            with col_ticker:
                st.markdown(f"**{item['ticker']}**")
            with col_btn:
                if st.button("❌ Usuń", key=f"del_watchlist_{item['id']}", use_container_width=True):
                    remove_from_watchlist(user_id, item['ticker'])
                    st.rerun()
    else:
        st.info("Twoja watchlista jest pusta.")


def display_alerts_tab(user_id, is_guest):
    if is_guest:
        render_guest_lock_ui("Alerty Cenowe", "🔐", "Ustawiaj powiadomienia cenowe i nie przegap żadnej okazji.")
        return

    st.subheader("Twoje Alerty Cenowe")
    with st.expander("➕ Dodaj nowy alert"):
        with st.form("add_alert_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            ticker_input = col1.text_input("Ticker", placeholder="np. TSLA")
            target_price = col2.number_input(
                "Cena docelowa", min_value=0.01, value=100.0, step=0.01, format="%.2f"
            )
            condition = col3.radio("Warunek", ["Powyżej", "Poniżej"], horizontal=True)

            submit_btn = st.form_submit_button("💾 Dodaj alert", type="primary", use_container_width=True)

            if submit_btn:
                if not ticker_input:
                    st.warning("Wpisz ticker spółki!")
                elif target_price <= 0:
                    st.warning("Cena docelowa musi być większa od 0!")
                else:
                    add_alert(
                        user_id,
                        ticker_input.upper(),
                        target_price,
                        "above" if condition == "Powyżej" else "below"
                    )
                    st.success(f"Dodano alert dla {ticker_input.upper()} ✅")
                    st.rerun()

    alerts = get_alerts(user_id)
    if alerts:
        st.markdown("---")
        st.markdown("##### Aktywne Alerty")
        for alert in alerts:
            col_card, col_btn = st.columns([1, 0.2])
            with col_card:
                st.markdown(render_styled_alert_card(alert), unsafe_allow_html=True)
            with col_btn:
                if st.button("❌ Usuń", key=f"del_alert_{alert['id']}", use_container_width=True):
                    remove_alert(alert['id'], user_id)
                    st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("Nie masz jeszcze żadnych aktywnych alertów.")


def display_news_cards(df):
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


def main():
    apply_custom_css()
    check_login()

    if 'user' not in st.session_state or st.session_state.user is None:
        render_login_page()
    else:
        if st.session_state.db_configured and st.session_state.mongo_configured and not st.session_state.clients_initialized:
            try:
                supabase_client, news_collection = initialize_clients(
                    supabase_url=st.session_state["sb_url"],
                    supabase_key=st.session_state["sb_api"],
                    mongo_uri=st.session_state["mongo_uri"],
                    mongo_db_name=st.session_state["mongo_db"]
                )
                st.session_state.supabase_client = supabase_client
                st.session_state.news_collection = news_collection
                st.session_state.clients_initialized = True
            except KeyError as e:
                st.error(f"Brakuje konfiguracji w st.session_state: {e}")
                st.stop()
            except Exception as e:
                st.error(f"Nie udało się zainicjować połączeń z bazami danych: {e}")
                st.stop()
        render_dashboard()


if __name__ == "__main__":
    main()
