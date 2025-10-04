import sys
import os
import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import streamlit.components.v1 as components

# --- Konfiguracja Ścieżek ---
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# --- Importy z modułów ---
from app.stocks import fetch_finviz
from app.save_data import save_stocks_to_csv
from app.news import fetch_google_news_rss, add_sentiment
from app.predictive_model import load_all_stocks_data, get_avg_sentiment_for_tickers
from app.web.auth import login, logout, register
from app.web.watchlist import get_watchlist, add_to_watchlist, remove_from_watchlist
from app.web.alerts import get_alerts, add_alert, remove_alert

# ----------------- INICJALIZACJA APLIKACJI -----------------
st.set_page_config(page_title="Stock AI Dashboard", layout="wide", page_icon="📈")


# --- Funkcja dDo ładowania animacji (zwraca teraz dane JSON) ---
def load_lottie_json(filepath: str):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


# --- NOWA FUNKCJA DLA ANIMACJI Z COOLDOWNEM ---
def display_lottie_with_cooldown(lottie_json):
    if not lottie_json:
        return

    # Konwertujemy dane JSON na string, aby wstrzyknąć je do JS
    animation_data_str = json.dumps(lottie_json)

    # HTML i JavaScript do kontrolowania animacji
    html_code = f"""
        <div id="lottie-container" style="width: 100%; height: 200px;"></div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>
        <script>
            var animationData = {animation_data_str};
            var container = document.getElementById('lottie-container');

            var anim = lottie.loadAnimation({{
                container: container,
                renderer: 'svg',
                loop: false, // Ważne: wyłączamy domyślne zapętlanie
                autoplay: true,
                animationData: animationData
            }});

            // Kiedy animacja się zakończy...
            anim.addEventListener('complete', function() {{
                // ...poczekaj 5 sekund...
                setTimeout(function() {{
                    // ...i odpal ją od nowa.
                    anim.play();
                }}, 5000); // 5000 milisekund = 5 sekund
            }});
        </script>
    """
    components.html(html_code, height=210)


# --- NOWY CSS Z CZCIONKĄ POPPINS ---
st.markdown("""
    <style>
    /* Import czcionki Poppins z Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');

    /* Ukrycie domyślnego menu Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Nowy styl dla tytułu na stronie logowania */
    .login-title {{
        font-family: 'Poppins', sans-serif;
        font-size: 2.5rem; /* Większa czcionka */
        font-weight: 700;
        text-align: center;
        color: #2A3B4D;
        margin-top: 20px;
        margin-bottom: 10px;
    }}
    .login-subtitle {{
        font-family: 'Poppins', sans-serif;
        text-align: center;
        color: #5A6B7D;
        margin-bottom: 30px;
    }}

    /* Style dla kart newsów (zostają bez zmian) */
    .news-card {{
        background-color: #f8f9fa; border-left: 4px solid #007bff; border-radius: 5px;
        padding: 1rem; margin-bottom: 1rem;
    }}
    .news-title a {{ font-size: 1.1rem; font-weight: 600; text-decoration: none; color: inherit; }}
    .news-meta {{ font-size: 0.85rem; color: #6c757d; }}
    .sentiment-badge {{ font-weight: 700; padding: 3px 10px; border-radius: 12px; font-size: 13px; color: #fff; }}
    .positive-bg {{ background-color: #28a745; }}
    .negative-bg {{ background-color: #dc3545; }}
    .neutral-bg {{ background-color: #6c757d; }}
    </style>
""", unsafe_allow_html=True)


def display_news_cards(df):
    # ... ta funkcja bez zmian
    pass


# ----------------- SEKCJA LOGOWANIA / REJESTRACJI (Z NOWYM WYGLĄDEM) -----------------
if "user" not in st.session_state or not st.session_state["user"]:
    lottie_json_data = load_lottie_json("assets/animation.json")

    _, col_main, _ = st.columns([1, 2, 1])
    with col_main:
        # Używamy nowej funkcji do animacji
        display_lottie_with_cooldown(lottie_json_data)

        st.markdown("<h1 class='login-title'>Witaj w Stock AI Dashboard</h1>", unsafe_allow_html=True)
        st.markdown("<p class='login-subtitle'>Zaloguj się lub utwórz konto, aby rozpocząć analizę.</p>",
                    unsafe_allow_html=True)

        choice = st.radio("Wybierz opcję:", ["Logowanie", "Rejestracja"], horizontal=True, label_visibility="collapsed")

        if choice == "Logowanie":
            with st.form("login_form", border=True):
                email = st.text_input("Email", placeholder="user@example.com")
                password = st.text_input("Hasło", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Zaloguj się", use_container_width=True, type="primary")
                if submitted:
                    if login(email, password):
                        st.rerun()
        else:
            with st.form("register_form", border=True):
                email = st.text_input("Email", placeholder="user@example.com")
                password = st.text_input("Hasło", type="password", placeholder="••••••••")
                submitted = st.form_submit_button("Zarejestruj się", use_container_width=True)
                if submitted:
                    register(email, password)
    st.stop()

# ----------------- GŁÓWNA CZĘŚĆ APLIKACJI (PO ZALOGOWANIU) -----------------
else:
    user = st.session_state["user"]

    # --- NAGŁÓWEK BEZ SIDEBARA ---
    col_title, col_user_panel = st.columns([0.7, 0.3])
    with col_title:
        st.title("📊 AI Stock Screener")
    with col_user_panel:
        col_icon, col_email, col_button = st.columns([1, 3, 2])
        with col_icon:
            st.markdown("""
                <div style="text-align: right; padding-top: 5px;">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="28" height="28">
                        <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                    </svg>
                </div>
            """, unsafe_allow_html=True)
        with col_email:
            st.markdown(f"<div style='padding-top: 8px;'>{user.email}</div>", unsafe_allow_html=True)
        with col_button:
            if st.button("Wyloguj"):
                logout()
                st.rerun()
    st.markdown("---")
    st.subheader("🔧 Połącz własną bazę danych")

    with st.form("db_config_form"):
        use_custom = st.checkbox("Chcę użyć własnej bazy", value=False)

        if use_custom:
            mongo_uri_input = st.text_input("MongoDB URI", placeholder="mongodb://user:pass@host:port/db")
            mongo_db_input = st.text_input("MongoDB DB name", placeholder="stocks_db")
            pg_url_input = st.text_input("PostgreSQL URL", placeholder=PG_URL_DEFAULT)
            pg_password_input = st.text_input("PostgreSQL Password", type="password")
            pg_key_input = st.text_input("PostgreSQL Key", type="password")
            sb_url_input = st.text_input("Supabase URL", placeholder=SB_URL_DEFAULT)
            sb_api_input = st.text_input("Supabase API", type="password")
            sb_password_input = st.text_input("Supabase Password", type="password")

        if st.form_submit_button("💾 Połącz"):
            if use_custom:
                st.session_state.update({
                    "mongo_uri": mongo_uri_input,
                    "mongo_db": mongo_db_input,
                    "pg_url": pg_url_input,
                    "pg_password": pg_password_input,
                    "pg_key": pg_key_input,
                    "sb_url": sb_url_input,
                    "sb_api": sb_api_input,
                    "sb_password": sb_password_input
                })
            st.success("✅ Połączono z wybraną bazą!")
            st.rerun()

    # --- ZAKŁADKI APLIKACJI ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📈 Dane giełdowe", "📰 Newsy", "🤖 Model predykcyjny", "❤️ Watchlista", "🔔 Alerty Cenowe"])

    user_id = user.id

    # ... Wszystkie taby od 1 do 5 wklej tutaj z poprzedniej, pełnej wersji ...
    # Poniżej wklejam je dla kompletności

    # ==================== TAB 1: DANE GIEŁDOWE ====================
    with tab1:
        st.subheader("Pobierz dane giełdowe z Finviz")
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            max_companies = col1.number_input("Ilość spółek (0 = wszystkie)", min_value=0, value=20, step=10,
                                              key="max_companies_tab1")
            with_filters = col2.checkbox("Filtry (Mid Cap, NASDAQ)", value=False, key="filters_tab1")
            get_only_tickers = col3.checkbox("Tylko tickery?", value=False, key="tickers_only_tab1")
        if st.button("🔄 Pobierz dane giełdowe", type="primary"):
            with st.spinner("Pobieram dane z Finviz..."):
                df = fetch_finviz(max_companies, with_filters, get_only_tickers)
                if not df.empty:
                    st.success(f"Pobrano {len(df)} spółek")
                    st.dataframe(df, use_container_width=True, height=500)
                    save_stocks_to_csv(df, get_only_tickers, with_filters)
                else:
                    st.error("❌ Nie udało się pobrać danych.")

    # ==================== TAB 2: NEWSY ====================
    with tab2:
        st.subheader("Newsy i analiza sentymentu")
        watchlist_tickers = [item['ticker'] for item in get_watchlist(user_id)]
        analysis_choice = st.radio("Wybierz źródło tickera:", ["Wpisz ręcznie", "Wybierz z obserwowanych"],
                                   horizontal=True, key="news_choice")

        if analysis_choice == "Wpisz ręcznie":
            ticker = st.text_input("🔎 Wpisz ticker (np. AAPL, TSLA)", key="ticker_news_tab2").upper()
        else:
            if not watchlist_tickers:
                st.warning("Twoja watchlista jest pusta. Dodaj spółki w zakładce '❤️ Watchlista'.")
                ticker = ""
            else:
                ticker = st.selectbox("Wybierz spółkę z Twojej watchlisty:", options=watchlist_tickers)

        if st.button("📥 Pobierz newsy dla spółki", type="primary"):
            if ticker:
                with st.spinner(f"Pobieram i analizuję newsy dla {ticker}..."):
                    df_news = fetch_google_news_rss(ticker)
                    if not df_news.empty:
                        df_news = add_sentiment(df_news)
                        avg_sent = df_news['sentiment'].mean()
                        c1, c2 = st.columns(2)
                        c1.metric("Średni sentyment", f"{avg_sent:.3f}")
                        c2.metric("Liczba newsów", len(df_news))
                        fig = px.histogram(df_news, x="sentiment", nbins=20, title=f"Rozkład sentymentu dla {ticker}")
                        st.plotly_chart(fig, use_container_width=True)
                        display_news_cards(df_news)
                    else:
                        st.warning(f"Brak newsów dla {ticker}")
            else:
                st.warning("Proszę wpisać lub wybrać ticker.")

    # ==================== TAB 3: MODEL PREYDYKCYJNY ====================
    with tab3:
        st.subheader("Predykcja na podstawie modelu i sentymentu")
        top_n = st.slider("📊 Liczba najlepszych spółek do wyświetlenia", min_value=5, max_value=50, value=20, step=5)

        if st.button("🚀 Uruchom model predykcyjny", type="primary"):
            with st.spinner("⏳ Analizuję dane historyczne i sentyment... Może to potrwać chwilę."):
                df_all = load_all_stocks_data()
                if not df_all.empty:
                    # Tutaj cała logika modelu
                    tickers = df_all['ticker'].dropna().unique()
                    dates = df_all['import_date'].dropna().unique()
                    all_sentiments = []
                    for day in dates:
                        sentiment_df = get_avg_sentiment_for_tickers(tickers, day)
                        sentiment_df['import_date'] = day
                        all_sentiments.append(sentiment_df)
                    sentiment_all = pd.concat(all_sentiments, ignore_index=True)
                    df_all = df_all.merge(sentiment_all, on=['ticker', 'import_date'], how='left').fillna(
                        {'avg_sentiment': 0.0})
                    df_all['market_cap_log'] = np.log1p(df_all['market_cap'].astype(float))
                    p_norm = (df_all['price'] - df_all['price'].min()) / (
                                df_all['price'].max() - df_all['price'].min() + 1e-9)
                    mc_norm = (df_all['market_cap_log'] - df_all['market_cap_log'].min()) / (
                                df_all['market_cap_log'].max() - df_all['market_cap_log'].min() + 1e-9)
                    min_sent, max_sent = df_all['avg_sentiment'].min(), df_all['avg_sentiment'].max()
                    sentiment_range = max_sent - min_sent if (max_sent - min_sent) != 0 else 1
                    sentiment_norm = (df_all['avg_sentiment'] - min_sent) / sentiment_range
                    df_all['potential_score'] = (0.4 * p_norm + 0.4 * mc_norm + 0.2 * sentiment_norm).fillna(0)
                    last_day = max(df_all['import_date'])
                    df_day = df_all[df_all['import_date'] == last_day].copy()


                    def explain_decision(row, df):
                        reasons = []
                        if row['price'] > df['price'].quantile(0.75): reasons.append("wysoka cena")
                        if row['market_cap_log'] > df['market_cap_log'].quantile(0.75): reasons.append(
                            "duża kapitalizacja")
                        if row['avg_sentiment'] > 0.1: reasons.append("bardzo pozytywny sentyment")
                        if row['potential_score'] > df['potential_score'].quantile(0.75): reasons.append(
                            "wysoki potencjał modelu")
                        return ", ".join(reasons) if reasons else "stabilne wskaźniki"


                    df_day['reason'] = df_day.apply(lambda r: explain_decision(r, df_day), axis=1)
                    top_day = df_day.sort_values('potential_score', ascending=False).head(top_n)
                    st.session_state.update(
                        {'model_run_success': True, 'df_all': df_all, 'top_day': top_day, 'last_day': last_day})
                else:
                    st.error("Brak danych historycznych. Uruchom skrypt zbierający dane.")

        if st.session_state.get('model_run_success', False):
            top_day = st.session_state['top_day']
            df_all = st.session_state['df_all']
            st.success(f"✅ Analiza zakończona. Oto Top {len(top_day)} spółek z dnia {st.session_state['last_day']}")
            st.dataframe(top_day[['ticker', 'company', 'potential_score', 'avg_sentiment', 'price', 'reason']],
                         use_container_width=True)

            st.markdown("---")
            st.subheader("Szczegółowa analiza wybranej spółki")
            chosen_ticker = st.selectbox("Wybierz spółkę z powyższej listy:", options=top_day['ticker'].unique())
            if chosen_ticker:
                stock_data = top_day[top_day['ticker'] == chosen_ticker].iloc[0]
                st.info(f"**Uzasadnienie wyboru:** {stock_data['reason']}")

    # ==================== TAB 4: WATCHLISTA ====================
    with tab4:
        st.subheader("❤️ Twoja Watchlista")
        with st.form("add_ticker_form", clear_on_submit=True):
            new_ticker = st.text_input("Dodaj ticker do obserwowanych:", placeholder="np. NVDA").upper()
            if st.form_submit_button("➕ Dodaj", use_container_width=True, type="primary"):
                if new_ticker:
                    add_to_watchlist(user_id, new_ticker)
                    st.rerun()
        st.markdown("---")
        st.markdown("#### Obecnie obserwujesz:")
        watchlist_data = get_watchlist(user_id)
        if not watchlist_data:
            st.info("Twoja watchlista jest pusta.")
        else:
            for item in watchlist_data:
                col1, col2 = st.columns([4, 1])
                col1.code(item['ticker'])
                if col2.button("🗑️ Usuń", key=f"del_watch_{item['id']}", use_container_width=True):
                    remove_from_watchlist(item['id'])
                    st.toast(f"Usunięto {item['ticker']} z obserwowanych.")
                    st.rerun()

    # ==================== TAB 5: ALERTY CENOWE ====================
    with tab5:
        st.subheader("🔔 Alerty Cenowe")
        with st.form("add_alert_form", clear_on_submit=True):
            alert_ticker = st.text_input("Ticker", placeholder="np. AAPL").upper()
            col_low, col_high = st.columns(2)
            threshold_low = col_low.number_input("Powiadom, gdy cena spadnie poniżej:", min_value=0.0, format="%.2f")
            threshold_high = col_high.number_input("Powiadom, gdy cena wzrośnie powyżej:", min_value=0.0, format="%.2f")
            if st.form_submit_button("🔔 Ustaw alert", use_container_width=True, type="primary"):
                if alert_ticker and (threshold_low > 0 or threshold_high > 0):
                    add_alert(user_id, alert_ticker, threshold_high, threshold_low)
                    st.rerun()
                else:
                    st.warning("Wpisz ticker i co najmniej jeden próg cenowy.")
        st.markdown("---")
        st.markdown("#### Twoje aktywne alerty:")
        active_alerts = get_alerts(user_id)
        if not active_alerts:
            st.info("Nie masz ustawionych żadnych alertów.")
        else:
            for alert in active_alerts:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        low_price = f"${alert['threshold_low']}" if alert['threshold_low'] else "Brak"
                        high_price = f"${alert['threshold_high']}" if alert['threshold_high'] else "Brak"
                        st.markdown(f"**{alert['ticker']}**")
                        st.markdown(
                            f"<span style='color: #dc3545;'>↓ {low_price}</span> | <span style='color: #28a745;'>↑ {high_price}</span>",
                            unsafe_allow_html=True)
                    if col2.button("🗑️ Usuń alert", key=f"del_alert_{alert['id']}", use_container_width=True):
                        remove_alert(alert['id'])
                        st.toast(f"Usunięto alert dla {alert['ticker']}.")
                        st.rerun()