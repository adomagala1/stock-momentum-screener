import sys
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Dodawanie ścieżki do folderu nadrzędnego, aby importy działały poprawnie
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.stocks import fetch_finviz
from app.news import fetch_google_news_rss, add_sentiment
from app.predictive_model import load_all_stocks_data, get_avg_sentiment_for_tickers
from app.web.auth import login, logout, register, check_login
from app.web.watchlist import get_watchlist, add_to_watchlist, remove_from_watchlist
from app.web.alerts import get_alerts, add_alert, ALERTS_CSS, render_styled_alert_card
from app.db.user_supabase_manager import clean_and_transform_for_db, SupabaseHandler

# Konfiguracja strony
st.set_page_config(page_title="Stock AI Dashboard", layout="wide", page_icon="📈")

# Inicjalizacja stanu sesji
if "user" not in st.session_state:
    st.session_state.user = None
if "is_guest" not in st.session_state:
    st.session_state.is_guest = False
if "db_configured" not in st.session_state:
    st.session_state.db_configured = False


# --- FUNKCJE POMOCNICZE UI ---
def apply_custom_css():
    st.markdown("""
        <style>
            [data-testid="stSidebar"] {background-color: #f8f9fa;}
            .stButton>button {border-radius: 8px;}
            h1, h2, h3 {color: #0d1b2a;}
            .news-card {
                background-color: #ffffff; border-radius: 10px; padding: 16px;
                margin-bottom: 12px; border: 1px solid #e6e6e6;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }
            .news-title a {
                text-decoration: none; color: #0d1b2a !important; font-weight: 600; font-size: 1.1em;
            }
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


def render_guest_lock_ui(title, icon, description):
    with st.container(border=True):
        st.markdown(f"### {icon} {title}")
        st.markdown(description)
        st.divider()
        if st.button("Zarejestruj się lub zaloguj, aby odblokować", type="primary", key=f"lock_{title}",
                     width="stretch"):
            logout()
            st.rerun()


# --- GŁÓWNE STRONY APLIKACJI ---
def render_login_page():
    _, col_main, _ = st.columns([1, 2, 1])
    with col_main:
        st.markdown("<h1 style='text-align: center;'>AI Stock Screener</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Zaloguj się, zarejestruj lub wejdź jako gość, aby rozpocząć.</p>",
                    unsafe_allow_html=True)

        choice = st.radio("Wybierz opcję:", ["Logowanie", "Rejestracja", "Tryb Gościa"], horizontal=True,
                          label_visibility="collapsed")

        if choice == "Logowanie":
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="user@example.com")
                password = st.text_input("Hasło", type="password", placeholder="••••••••")
                if st.form_submit_button("Zaloguj się", width="stretch", type="primary"):
                    if login(email, password):
                        st.session_state.is_guest = False
                        st.rerun()
        elif choice == "Rejestracja":
            with st.form("register_form"):
                email = st.text_input("Email", placeholder="user@example.com")
                password = st.text_input("Hasło", type="password", placeholder="••••••••")
                if st.form_submit_button("Zarejestruj się", width="stretch"):
                    register(email, password)
        elif choice == "Tryb Gościa":
            st.info(
                "Tryb gościa pozwala na przeglądanie danych i testowanie modelu. Personalizacja (watchlisty, alerty) wymaga zalogowania.",
                icon="ℹ️")
            if st.button("Kontynuuj jako Gość", width="stretch"):
                st.session_state.user = {"email": "Gość", "id": None}
                st.session_state.is_guest = True
                st.toast("✅ Uruchomiono tryb gościa.")
                st.rerun()


def render_dashboard():
    user, is_guest = st.session_state.user, st.session_state.is_guest

    # --- NOWY WSKAŹNIK STATUSU BAZY DANYCH ---
    db_status_color = "green" if st.session_state.get("db_configured") else "red"
    db_status_text = "Połączono" if st.session_state.get("db_configured") else "Brak połączenia"
    db_status_badge = f'<span style="background-color: {db_status_color}; color: white; padding: 4px 10px; border-radius: 15px; font-size: 12px; font-weight: bold; vertical-align: middle; margin-left: 15px;">BAZA DANYCH: {db_status_text}</span>'

    col_title, col_user = st.columns([0.7, 0.3])
    with col_title:
        # Dodajemy plakietkę do tytułu
        st.markdown(f"<h1>AI Stock Screener {db_status_badge}</h1>", unsafe_allow_html=True)

    with col_user:
        if is_guest:
            if st.button("Zaloguj / Zarejestruj się", width="stretch"):
                logout()
                st.rerun()
        else:
            user_email = user.email if hasattr(user, 'email') else user.get('email', 'Nieznany')
            st.markdown(f"<div style='text-align: right;'>Zalogowano jako:<br><b>{user_email}</b></div>",
                        unsafe_allow_html=True)
            if st.button("Wyloguj", width="stretch", type="secondary"):
                logout()
                st.rerun()
    st.divider()

    # --- OPCJONALNA SEKCJA KONFIGURACJI BAZY DANYCH ---
    with st.expander("⚙️ Konfiguracja Połączenia z Bazą Danych"):
        db_choice = st.radio(
            "Wybierz sposób połączenia:",
            ["Użyj domyślnej konfiguracji (z secrets.toml)", "Użyj mojej własnej konfiguracji"],
            horizontal=True,
            key="db_choice"
        )

        if db_choice == "Użyj mojej własnej konfiguracji":
            with st.form("db_custom_form"):
                st.markdown("##### Połączenie z Supabase")
                sb_url_input = st.text_input("Supabase URL", placeholder="https:// TwojeID .supabase.co",
                                             value=st.session_state.get("sb_url", ""))
                sb_api_input = st.text_input("Supabase API Key (anon key)", type="password")
                if st.form_submit_button("💾 Zapisz i połącz", type="primary", width="stretch"):
                    if sb_url_input and sb_api_input:
                        st.session_state.update({"sb_url": sb_url_input, "sb_api": sb_api_input, "db_configured": True})
                        st.success("Konfiguracja Supabase zapisana.")
                        st.rerun()
                    else:
                        st.error("Proszę wypełnić oba pola.")
        else:  # Opcja domyślna
            if st.button("Połącz używając konfiguracji domyślnej", width="stretch"):
                try:
                    # Sprawdzamy czy secrets istnieją
                    if "sb_url" in st.secrets and "sb_api" in st.secrets:
                        sb_url = st.secrets["sb_url"]
                        sb_api = st.secrets["sb_api"]
                        st.session_state.update({"sb_url": sb_url, "sb_api": sb_api, "db_configured": True})
                        st.success("Połączono z bazą danych używając domyślnej konfiguracji.")
                        st.rerun()
                    else:
                        st.error("Brak wymaganych kluczy 'sb_url' i 'sb_api' w pliku secrets.toml.")
                except Exception:
                    st.error(
                        "Nie można załadować `secrets.toml`. Upewnij się, że plik istnieje i ma poprawną strukturę.")

        # Opcja rozłączenia
        if st.session_state.get("db_configured"):
            st.info(f"Aktualne połączenie: {st.session_state.get('sb_url')}")
            if st.button("🔌 Rozłącz z bazą danych", width="stretch"):
                st.session_state["db_configured"] = False
                st.session_state["sb_url"] = ""
                st.session_state["sb_api"] = ""
                st.rerun()

    # --- Renderowanie zakładek ---
    user_id = user.id if hasattr(user, 'id') else user.get('id')
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📈 Dane giełdowe", "📰 Newsy", "🤖 Model predykcyjny", "❤️ Watchlista", "🔔 Alerty Cenowe"])

    display_stocks_tab(tab1)
    display_news_tab(tab2, user_id, is_guest)
    display_model_tab(tab3)
    display_watchlist_tab(tab4, user_id, is_guest)
    display_alerts_tab(tab5, user_id, is_guest)


# --- WYŚWIETLANIE ZAKŁADEK Z NOWĄ LOGIKĄ ---
def display_stocks_tab(tab_container):
    with tab_container:
        st.subheader("Pobierz dane giełdowe z Finviz")
        with st.expander("⚙️ Ustawienia pobierania"):
            max_companies = st.number_input("Maksymalna ilość spółek (0 = wszystkie)", min_value=0, value=50, step=10)
            get_only_tickers = st.checkbox("Tylko tickery)", value=False)
            with_filters = st.checkbox("Filtry", value=False)

        if st.button("🔄 Pobierz dane giełdowe", type="primary", width="stretch"):
            with st.spinner("Pobieram dane z Finviz..."):
                try:
                    df = fetch_finviz(max_companies=max_companies, get_only_tickers=get_only_tickers,
                                      with_filters=with_filters)
                    if df.empty:
                        st.warning("Nie znaleziono danych dla podanych kryteriów.")
                    else:
                        st.success(f"Pobrano dane dla {len(df)} spółek.")
                        st.dataframe(df)
                        st.session_state["latest_df"] = df
                except Exception as e:
                    st.error(f"Nie udało się pobrać danych: {e}")

        # ZMIANA LOGIKI: Przycisk zapisu jest teraz warunkowy
        if "latest_df" in st.session_state:
            if not st.session_state.get("db_configured"):
                st.warning("Skonfiguruj połączenie z bazą danych, aby móc zapisać dane.", icon="ℹ️")
                st.button("💾 Zapisz do Supabase", type="secondary", width="stretch", disabled=True)
            else:
                if st.button("💾 Zapisz do Supabase", type="secondary", width="stretch"):
                    with st.spinner("Przygotowuję i zapisuję dane do Supabase..."):
                        df_raw = st.session_state.get("latest_df")
                        df_cleaned = clean_and_transform_for_db(df_raw)
                        try:
                            sb = SupabaseHandler(st.session_state["sb_url"], st.session_state["sb_api"])
                            saved_count = sb.save_dataframe(df_cleaned, table_name="stocks_data")
                            if saved_count > 0:
                                st.success(f"✅ Pomyślnie zapisano {saved_count} rekordów do Supabase!")
                            else:
                                st.error("❌ Nie udało się zapisać rekordów. Sprawdź komunikaty powyżej lub w konsoli.")
                        except Exception as e:
                            st.error(f"❌ Wystąpił krytyczny błąd podczas zapisu: {e}")


def display_news_tab(tab_container, user_id, is_guest):
    with tab_container:
        st.subheader("Analiza sentymentu na podstawie newsów")
        ticker = None
        if is_guest:
            ticker = st.text_input("🔎 Wpisz ticker (np. AAPL, TSLA)", key="news_ticker_guest").upper()
        else:
            if st.session_state.get("db_configured"):
                watchlist = get_watchlist(user_id) if user_id else []
                watchlist_tickers = [item['ticker'] for item in watchlist] if watchlist else []
                ticker = st.selectbox("Wybierz spółkę z Twojej watchlisty lub wpisz poniżej:",
                                      options=[""] + watchlist_tickers) or st.text_input("🔎 Wpisz ticker ręcznie",
                                                                                         key="news_ticker_user").upper()
            else:
                ticker = st.text_input("🔎 Wpisz ticker (np. AAPL, TSLA)", key="news_ticker_no_db").upper()

        if st.button("📥 Pobierz i analizuj newsy", type="primary", width="Stretch"):
            if ticker:
                with st.spinner(f"Analizuję newsy dla {ticker}..."):
                    df_news = fetch_google_news_rss(ticker)
                    if not df_news.empty:
                        df_news = add_sentiment(df_news)
                        st.markdown(f"#### Wyniki dla: **{ticker}**")
                        cols = st.columns(2)
                        cols[0].metric("Średni sentyment", f"{df_news['sentiment'].mean():.3f}")
                        cols[1].metric("Liczba newsów", len(df_news))
                        fig = px.histogram(df_news, x="sentiment", nbins=20, title=f"Rozkład sentymentu dla {ticker}")
                        st.plotly_chart(fig, width="Stretch")
                        display_news_cards(df_news)
                    else:
                        st.warning(f"Nie znaleziono nowszych wiadomości dla tickera {ticker}.")
            else:
                st.warning("Proszę wpisać lub wybrać ticker do analizy.")


def display_model_tab(tab_container):
    with tab_container:
        st.subheader("Model predykcyjny AI")
        st.info("Model ocenia spółki na podstawie ceny, kapitalizacji i sentymentu. Do działania wymaga danych z bazy.",
                icon="💡")
        top_n = st.slider("📊 Ile najlepszych spółek wyświetlić?", 5, 50, 20, 5)

        if not st.session_state.get("db_configured"):
            st.warning(
                "Model predykcyjny wymaga połączenia z bazą danych do załadowania danych historycznych. Proszę skonfigurować połączenie.",
                icon="⚠️")
            st.button("🚀 Uruchom model", type="primary", width="stretch", disabled=True)
        else:
            if st.button("🚀 Uruchom model", type="primary", width="stretch"):
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
            st.warning("Watchlista wymaga połączenia z bazą danych. Proszę skonfigurować połączenie.", icon="⚠️")
            return

        st.subheader("Twoja Watchlista")
        watchlist = get_watchlist(user_id)
        tickers = [w['ticker'] for w in watchlist] if watchlist else []

        if tickers:
            st.dataframe(pd.DataFrame(tickers, columns=["Obserwowane Tickery"]), width="stretch",
                         hide_index=True)
        else:
            st.info("Twoja watchlista jest pusta.")

        col1, col2 = st.columns(2)
        with col1:
            with st.form("add_watchlist_form"):
                ticker_input = st.text_input("Dodaj spółkę do watchlisty", placeholder="np. AAPL")
                if st.form_submit_button("➕ Dodaj", type="primary", width="stretch"):
                    if ticker_input:
                        add_to_watchlist(user_id, ticker_input.upper())
                        st.toast(f"Dodano {ticker_input.upper()} do watchlisty.")
                        st.rerun()
        with col2:
            if tickers:
                with st.form("remove_watchlist_form"):
                    ticker_remove = st.selectbox("Usuń spółkę z watchlisty", options=tickers)
                    if st.form_submit_button("❌ Usuń", type="secondary", width="stretch"):
                        remove_from_watchlist(user_id, ticker_remove)
                        st.toast(f"Usunięto {ticker_remove} z watchlisty.")
                        st.rerun()


def display_alerts_tab(tab_container, user_id, is_guest):
    with tab_container:
        st.markdown(ALERTS_CSS, unsafe_allow_html=True)
        if is_guest:
            render_guest_lock_ui("Alerty Cenowe", "🔔",
                                 "Ustawiaj powiadomienia cenowe i nie przegap żadnej okazji. Ta funkcja wymaga konta użytkownika.")
            return
        if not st.session_state.get("db_configured"):
            st.warning("Alerty cenowe wymagają połączenia z bazą danych. Proszę skonfigurować połączenie.", icon="⚠️")
            return

        st.subheader("Alerty cenowe")
        alerts = get_alerts(user_id) if user_id else []
        if not alerts:
            st.info("Nie masz jeszcze żadnych aktywnych alertów.")
        else:
            for alert in alerts:
                render_styled_alert_card(alert, user_id)

        with st.expander("➕ Dodaj nowy alert"):
            with st.form("add_alert_form"):
                ticker_input = st.text_input("Ticker", placeholder="np. TSLA")
                target_price = st.number_input("Cena docelowa", min_value=0.01, value=100.0, step=0.01, format="%.2f")
                condition = st.radio("Warunek", ["Powyżej", "Poniżej"], horizontal=True)
                if st.form_submit_button("💾 Dodaj alert", type="primary", width="stretch"):
                    if ticker_input:
                        add_alert(user_id, ticker_input.upper(), target_price,
                                  "above" if condition == "Powyżej" else "below")
                        st.toast(f"Alert dla {ticker_input.upper()} został dodany.")
                        st.rerun()


# --- GŁÓWNA FUNKCJA URUCHAMIAJĄCA ---
def main():
    apply_custom_css()
    check_login()

    if st.session_state.get('user') is None:
        render_login_page()
    else:
        render_dashboard()


if __name__ == "__main__":
    main()
