import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

from app.stocks import fetch_finviz
from app.save_data import save_stocks_to_csv
from app.news import fetch_google_news_rss, add_sentiment
from app.predictive_model import load_all_stocks_data, get_avg_sentiment_for_tickers
from app.web.auth import login, logout, register
from app.web.watchlist import get_watchlist, add_to_watchlist, remove_from_watchlist
from app.web.alerts import get_alerts, add_alert, remove_alert, ALERTS_CSS, render_styled_alert_card

# ----------------- INICJALIZACJA APLIKACJI -----------------
st.set_page_config(page_title="Stock AI Dashboard", layout="wide", page_icon="📈")

# --- Inicjalizacja stanu sesji ---
if "user" not in st.session_state:
    st.session_state.user = None
if "is_guest" not in st.session_state:
    st.session_state.is_guest = False
if "model_run_success" not in st.session_state:
    st.session_state.model_run_success = False


# ----------------- FUNKCJE POMOCNICZE -----------------

def apply_custom_css():
    """Aplikuje subtelne, niestandardowe style CSS do aplikacji."""
    st.markdown("""
        <style>
            /* --- Style dla kart z Newsami --- */
            .news-card {
                background-color: #ffffff;
                border-radius: 10px;
                padding: 16px;
                margin-bottom: 12px;
                border: 1px solid #e6e6e6;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }
            .news-title a {
                text-decoration: none;
                color: #0d1b2a !important;
                font-weight: 600;
                font-size: 1.1em;
            }
            .news-title a:hover { text-decoration: underline; }
            .news-meta { font-size: 0.85em; color: #6c757d; margin-top: 8px; }
            .sentiment-badge { display: inline-block; padding: 3px 10px; border-radius: 15px; font-weight: 500; color: white; font-size: 0.8em; }
            .positive-bg { background-color: #28a745; }
            .negative-bg { background-color: #dc3545; }
            .neutral-bg { background-color: #6c757d; }
        </style>
    """, unsafe_allow_html=True)


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


def render_guest_lock_ui(title, icon, description):
    """Renderuje estetyczny placeholder dla funkcji dostępnych po zalogowaniu, używając natywnych komponentów Streamlit."""
    with st.container(border=True):
        st.markdown(f"### {icon} {title}")
        st.markdown(description)
        st.divider()
        if st.button("Zarejestruj się lub zaloguj, aby odblokować", type="primary", use_container_width=True):
            logout()  # Czyści stan sesji
            st.rerun()


# ----------------- SEKCJE APLIKACJI (RENDEROWANIE UI) -----------------

def render_login_page():
    """Renderuje stronę logowania, rejestracji i wejścia jako gość."""
    _, col_main, _ = st.columns([1, 2, 1])
    with col_main:
        st.markdown("<h1 style='text-align: center;'>Ur stock screer dashboard</h1>", unsafe_allow_html=True)
        st.markdown(
            "<p style='text-align: center;'>Zaloguj się, zarejestruj lub wejdź jako gość, by zerknąć </p>",
            unsafe_allow_html=True)

        choice = st.radio("Wybierz opcję:", ["Logowanie", "Rejestracja", "Tryb Gościa"], horizontal=True,
                          label_visibility="collapsed")
        if choice == "Logowanie":
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="user@example.com")
                password = st.text_input("Hasło", type="password", placeholder="••••••••")
                if st.form_submit_button("Zaloguj się", use_container_width=True, type="primary"):
                    if login(email, password):
                        st.session_state.is_guest = False
                        st.rerun()
        elif choice == "Rejestracja":
            with st.form("register_form"):
                email = st.text_input("Email", placeholder="user@example.com")
                password = st.text_input("Hasło", type="password", placeholder="••••••••")
                if st.form_submit_button("Zarejestruj się", use_container_width=True):
                    register(email, password)
        elif choice == "Tryb Gościa":
            st.info(
                "Tryb gościa pozwala na przeglądanie ogólnodostępnych danych i testowanie modelu predykcyjnego. Personalizacja (watchlista, alerty) A TAKZE MODEL PREDYCYKJNY wymaga zalogowania",
                icon="ℹ️")
            if st.button("Kontynuuj jako Gość", use_container_width=True):
                st.session_state.user = {"email": "Gość", "id": None}
                st.session_state.is_guest = True
                st.toast("✅ Uruchomiono tryb gościa.")
                st.rerun()


def render_dashboard():
    """Renderuje główny dashboard aplikacji."""
    user, is_guest = st.session_state.user, st.session_state.is_guest

    col_title, col_user = st.columns([0.7, 0.3])
    with col_title:
        st.title("📊 AI Stock Screener")
    with col_user:
        if is_guest:
            if st.button("Zaloguj / Zarejestruj się", use_container_width=True):
                logout()
                st.rerun()
        else:
            with st.container():
                st.markdown(f"<div style='text-align: right;'>Zalogowano jako:<br><b>{user['email']}</b></div>",
                            unsafe_allow_html=True)
                if st.button("Wyloguj", use_container_width=True, type="secondary"):
                    logout()
                    st.rerun()
    st.divider()
    st.subheader("🔧 Konfiguracja połączenia z bazą danych")

    if "db_configured" not in st.session_state:
        def safe_get(secret_name, fallback_value):
            try:
                val = st.secrets.get(secret_name)
                if val is None or val == "":
                    return fallback_value
                return val
            except Exception:
                return fallback_value

        default_mongo_uri = safe_get("default_mongo_uri", "⚠️ Brak wartości (fallback)")
        default_mongo_db = safe_get("default_mongo_db", "⚠️ Brak wartości (fallback)")

        default_pg_url = safe_get("default_pg_url", "⚠️ Brak wartości (fallback)")
        default_pg_password = safe_get("default_pg_password", "⚠️ Brak wartości (fallback)")
        default_pg_key = safe_get("default_pg_key", "⚠️ Brak wartości (fallback)")

        default_sb_url = safe_get("default_sb_url", "⚠️ Brak wartości (fallback)")
        default_sb_api = safe_get("default_sb_api", "⚠️ Brak wartości (fallback)")
        default_sb_password = safe_get("default_sb_password", "⚠️ Brak wartości (fallback)")

        db_choice = st.radio(
            "Wybierz sposób połączenia:",
            ["🔒 Użyj mojej własnej konfiguracji", "⚙️ Użyj domyślnej konfiguracji (z secrets.toml lub fallback)"],
            horizontal=True,
        )

        if db_choice == "🔒 Użyj mojej własnej konfiguracji":
            with st.form("db_custom_form"):
                st.markdown(
                    '<h3 style="text-align: center; color: #007bff;">MongoDB newsy</h1>',
                    unsafe_allow_html=True
                )
                mongo_uri_input = st.text_input("MongoDB URI", placeholder="mongodb://user:pass@host:port/db")
                mongo_db_input = st.text_input("MongoDB DB name", placeholder="stocks_db")

                st.divider()

                st.markdown(
                    '<h3 style="text-align: center; color: #007bff;">PostgreSQL / Supabase Stock</h1>',
                    unsafe_allow_html=True
                )
                db_choice1, db_choice2 = st.columns(2)

                with db_choice1:
                    pg_url_input = st.text_input("PostgreSQL URL", placeholder="https://example.supabase.co")
                    pg_password_input = st.text_input("PostgreSQL Password", type="password")
                    pg_key_input = st.text_input("PostgreSQL Key (anon key)", type="password")

                with db_choice2:
                    sb_url_input = st.text_input("Supabase URL", placeholder="https://example.supabase.co")
                    sb_api_input = st.text_input("Supabase API Key", type="password")
                    sb_password_input = st.text_input("Supabase Password", type="password")

                if st.form_submit_button("💾 Zapisz połączenie", type="primary"):
                    st.session_state.update({
                        "mongo_uri": mongo_uri_input,
                        "mongo_db": mongo_db_input,
                        "pg_url": pg_url_input,
                        "pg_password": pg_password_input,
                        "pg_key": pg_key_input,
                        "sb_url": sb_url_input,
                        "sb_api": sb_api_input,
                        "sb_password": sb_password_input,
                        "db_mode": "custom",
                        "db_configured": True
                    })
                    st.success("✅ Zapisano niestandardową konfigurację bazy danych. Uruchom ponownie aplikację.")
                    st.rerun()
        else:
            st.session_state.update({
                "mongo_uri": st.secrets.get("mongo_uri", default_mongo_uri),
                "mongo_db": st.secrets.get("mongo_db", default_mongo_db),
                "pg_url": st.secrets.get("pg_url", default_pg_url),
                "pg_password": st.secrets.get("pg_password", default_pg_password),
                "pg_key": st.secrets.get("pg_key", default_pg_key),
                "sb_url": st.secrets.get("sb_url", default_sb_url),
                "sb_api": st.secrets.get("sb_api", default_sb_api),
                "sb_password": st.secrets.get("sb_password", default_sb_password),
                "db_mode": "default",
                "db_configured": True
            })
            st.success("✅ Używana jest domyślna konfiguracja połączenia z bazą danych.")
    else:
        st.info("🔗 Połączenie z bazą danych jest już skonfigurowane.")

    #aktualne dane
    with st.expander("🔧 Pokaż dane konfiguracyjne"):
        st.text(f"pg_url: {st.session_state.get('pg_url', 'brak')}")
        st.text(f"pg_password: {st.session_state.get('pg_password', 'brak')}")
        st.text(f"pg_key: {st.session_state.get('pg_key', 'brak')}")
        st.text(f"sb_url: {st.session_state.get('sb_url', 'brak')}")
        st.text(f"sb_api: {st.session_state.get('sb_api', 'brak')}")
        st.text(f"sb_password: {st.session_state.get('sb_password', 'brak')}")
        st.text(f"mongo_uri: {st.session_state.get('mongo_uri', 'brak')}")
        st.text(f"mongo_db: {st.session_state.get('mongo_db', 'brak')}")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📈 Dane giełdowe", "📰 Newsy", "🤖 Model predykcyjny", "❤️ Watchlista", "🔔 Alerty Cenowe"])

    display_stocks_tab(tab1)
    display_news_tab(tab2, user.get('id'), is_guest)
    display_model_tab(tab3)
    display_watchlist_tab(tab4, user.get('id'), is_guest)
    display_alerts_tab(tab5, user.get('id'), is_guest)


def display_stocks_tab(tab_container):
    with tab_container:
        st.subheader("Pobierz dane giełdowe z Finviz")
        st.caption("Użyj poniższych opcji, aby pobrać najnowsze dane o spółkach i zapisać je do analizy.")

        with st.expander("⚙️ Ustawienia pobierania"):
            max_companies = st.number_input("Maksymalna ilość spółek (0 = wszystkie)", min_value=0, value=20, step=10)
            with_filters = st.checkbox("Pobierz tylko tickery (szybciej)", value=False)
            get_only_tickers = st.checkbox("Zastosuj filtry (Mid Cap, NASDAQ)", value=False)

        if st.button("🔄 Pobierz dane giełdowe", type="primary", use_container_width=True):
            with st.spinner("Pobieram dane z Finviz..."):
                df = fetch_finviz(max_companies, with_filters, get_only_tickers)
                if not df.empty:
                    st.success(f"Pobrano dane dla {len(df)} spółek.")
                    st.dataframe(df, use_container_width=True, height=500)
                    save_stocks_to_csv(df, get_only_tickers, with_filters)
                else:
                    st.error("❌ Nie udało się pobrać danych. Spróbuj ponownie później.")


def display_news_tab(tab_container, user_id, is_guest):
    with tab_container:
        st.subheader("Analiza sentymentu na podstawie newsów")
        st.caption("Wpisz ticker spółki, aby pobrać najnowsze wiadomości i zobaczyć ich analizę sentymentu.")

        if is_guest:
            ticker = st.text_input("🔎 Wpisz ticker (np. AAPL, TSLA)", key="news_ticker_guest").upper()
            st.info("Załóż konto, aby móc szybko wybierać spółki ze swojej spersonalizowanej watchlisty!", icon="⭐")
        else:
            watchlist_tickers = [item['ticker'] for item in get_watchlist(user_id)]
            options = ["Wpisz ręcznie"]
            if watchlist_tickers: options.append("Wybierz z obserwowanych")

            analysis_choice = st.radio("Wybierz źródło tickera:", options, horizontal=True)
            if analysis_choice == "Wpisz ręcznie":
                ticker = st.text_input("🔎 Wpisz ticker (np. AAPL, TSLA)", key="news_ticker_user").upper()
            else:
                ticker = st.selectbox("Wybierz spółkę z Twojej watchlisty:", options=watchlist_tickers,
                                      key="news_ticker_select")

        if st.button("📥 Pobierz i analizuj newsy", type="primary", use_container_width=True):
            if ticker:
                with st.spinner(f"Pracuję nad analizą dla {ticker}..."):
                    df_news = fetch_google_news_rss(ticker)
                    if not df_news.empty:
                        df_news = add_sentiment(df_news)
                        st.divider()
                        st.markdown(f"**Wyniki dla: {ticker}**")
                        cols = st.columns(2)
                        cols[0].metric("Średni sentyment", f"{df_news['sentiment'].mean():.3f}")
                        cols[1].metric("Liczba przeanalizowanych newsów", len(df_news))
                        fig = px.histogram(df_news, x="sentiment", nbins=20, title=f"Rozkład sentymentu dla {ticker}")
                        st.plotly_chart(fig, use_container_width=True)
                        display_news_cards(df_news)
                    else:
                        st.warning(f"Nie znaleziono nowszych wiadomości dla tickera {ticker}.")
            else:
                st.warning("Proszę wpisać lub wybrać ticker do analizy.")


def display_model_tab(tab_container):
    with tab_container:
        st.subheader("Model predykcyjny AI")
        st.info(
            "Model ocenia spółki na podstawie ceny, kapitalizacji rynkowej i uśrednionego sentymentu z newsów, tworząc 'Potential Score'. Im wyższy wynik, tym większy potencjał według modelu.",
            icon="💡")

        top_n = st.slider("📊 Wybierz, ile najlepszych spółek wyświetlić", 5, 50, 20, 5)

        if st.button("🚀 Uruchom model", type="primary", use_container_width=True):
            with st.spinner("Analizuję dane i uruchamiam model... To może potrwać chwilę."):
                df_all = load_all_stocks_data()
                if not df_all.empty:
                    # Logika modelu pozostaje bez zmian
                    tickers = df_all['ticker'].dropna().unique()
                    dates = df_all['import_date'].dropna().unique()
                    all_sentiments = [get_avg_sentiment_for_tickers(tickers, day) for day in dates]
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
                        if row['avg_sentiment'] > 0.1: reasons.append("pozytywny sentyment")
                        if row['potential_score'] > df['potential_score'].quantile(0.75): reasons.append(
                            "wysoki potencjał")
                        return ", ".join(reasons) if reasons else "stabilne wskaźniki"

                    df_day['reason'] = df_day.apply(lambda r: explain_decision(r, df_day), axis=1)
                    top_day = df_day.sort_values('potential_score', ascending=False).head(top_n)
                    st.session_state.update({'model_run_success': True, 'top_day': top_day, 'last_day': last_day})
                else:
                    st.error("Brak danych historycznych do analizy. Pobierz dane w pierwszej zakładce.")

        if st.session_state.get('model_run_success'):
            st.divider()
            st.success(
                f"Oto Top {len(st.session_state.top_day)} spółek z dnia {st.session_state.last_day} według modelu:")
            st.dataframe(
                st.session_state.top_day[['ticker', 'company', 'potential_score', 'avg_sentiment', 'price', 'reason']],
                use_container_width=True)


def display_watchlist_tab(tab_container, user_id, is_guest):
    with tab_container:
        if is_guest:
            render_guest_lock_ui(
                title="Twoja osobista Watchlista", icon="❤️",
                description="Zapisuj interesujące Cię spółki, aby mieć je pod ręką ogołnie. Śledź ich wyniki i analizuj newsy w jednym miejscu. Mozesz zapisac do swojej bazy danych itp Ta funkcja jest dostępna po zalozeniu konta"
            )
            return

        st.subheader("❤️ Twoja Watchlista")
        with st.form("add_ticker_form", clear_on_submit=True):
            new_ticker = st.text_input("Dodaj ticker do obserwowanych:", placeholder="np. NVDA").upper()
            if st.form_submit_button("➕ Dodaj do watchlisty", use_container_width=True, type="primary"):
                if new_ticker:
                    add_to_watchlist(user_id, new_ticker)
                    st.rerun()

        st.divider()
        st.markdown("#### Obecnie obserwujesz:")
        watchlist_data = get_watchlist(user_id)
        if not watchlist_data:
            st.info("Twoja watchlista jest pusta. Dodaj ticker powyżej, aby zacząć obserwować.")
        else:
            for item in watchlist_data:
                col1, col2 = st.columns([4, 1])
                col1.code(item['ticker'])
                if col2.button("🗑️ Usuń", key=f"del_watch_{item['id']}", use_container_width=True):
                    remove_from_watchlist(item['id'])
                    st.rerun()


def display_alerts_tab(tab_container, user_id, is_guest):
    with tab_container:
        if is_guest:
            render_guest_lock_ui(
                title="Automatyczne Alerty Cenowe", icon="🔔",
                description="Nie przegap żadnej okazji! Ustaw progi cenowe dla wybranych spółek, a system powiadomi Cię, gdy cena osiągnie docelowy poziom. Ta funkcja jest dostępna po założeniu darmowego konta."
            )
            return

        st.markdown(ALERTS_CSS, unsafe_allow_html=True)

        st.subheader("🔔 Ustaw nowe Alerty Cenowe")
        with st.form("add_alert_form", clear_on_submit=True):
            alert_ticker = st.text_input("Ticker", placeholder="np. AAPL").upper()
            col_low, col_high = st.columns(2)
            threshold_low_input = col_low.text_input("Powiadom, gdy cena spadnie poniżej:", placeholder="np. 150.00")
            threshold_high_input = col_high.text_input("Powiadom, gdy cena wzrośnie powyżej:", placeholder="np. 200.00")

            threshold_low = float(threshold_low_input) if threshold_low_input.strip() else None
            threshold_high = float(threshold_high_input) if threshold_high_input.strip() else None

            if st.form_submit_button("🔔 Ustaw alert", use_container_width=True, type="primary"):
                if not alert_ticker:
                    st.warning("Podaj ticker.")
                elif threshold_low is None and threshold_high is None:
                    st.warning("Podaj co najmniej jeden próg cenowy.")
                else:
                    add_alert(user_id, alert_ticker, threshold_high or 0, threshold_low or 0)
                    st.rerun()

        st.divider()
        st.markdown("#### Twoje aktywne alerty:")
        active_alerts = get_alerts(user_id)
        if not active_alerts:
            st.info("Nie masz ustawionych żadnych alertów.")
        else:
            for alert in active_alerts:
                html = render_styled_alert_card(alert)
                st.markdown(html, unsafe_allow_html=True)

                cols = st.columns([3, 1])
                with cols[1]:
                    if st.button("🗑️ Usuń alert", key=f"del_alert_{alert['id']}", use_container_width=True):
                        remove_alert(alert['id'])
                        st.rerun()


def main():
    """Główna funkcja uruchamiająca aplikację."""
    apply_custom_css()
    if not st.session_state.user:
        render_login_page()
    else:
        render_dashboard()


if __name__ == "__main__":
    main()
