import streamlit as st
from supabase import create_client
from sqlalchemy import create_engine, text
from pymongo import MongoClient

# --------------------- SUPABASE (lub POSTGRES) ---------------------
def setup_supabase_tables():
    try:
        sb_url = st.session_state.get("sb_url")
        sb_key = st.session_state.get("sb_api")

        client = create_client(sb_url, sb_key)
        tables = ["stocks_data", "user_models", "watchlist", "alerts"]

        existing = client.table("pg_tables").select("*").execute()
        existing_names = [t["tablename"] for t in existing.data] if existing.data else []

        for t in tables:
            if t not in existing_names:
                # Tworzymy przykładową strukturę (dopasuj pod swoje potrzeby)
                if t == "stocks_data":
                    client.table("stocks_data").insert({
                        "ticker": "AAPL",
                        "import_date": "2025-01-01T00:00:00Z",
                        "close": 100.0,
                        "volume": 1000000,
                        "sentiment": 0.1
                    }).execute()
                elif t == "user_models":
                    client.table("user_models").insert({
                        "user_id": "test",
                        "model_results": [],
                        "created_at": "2025-01-01T00:00:00Z"
                    }).execute()
                elif t == "watchlist":
                    client.table("watchlist").insert({
                        "user_id": "test",
                        "ticker": "TSLA"
                    }).execute()
                elif t == "alerts":
                    client.table("alerts").insert({
                        "user_id": "test",
                        "ticker": "AAPL",
                        "target_price": 200,
                        "trigger": "Powyżej"
                    }).execute()

        st.success("✅ Supabase: automatyczna inicjalizacja zakończona.")
    except Exception as e:
        st.warning(f"⚠️ Błąd podczas inicjalizacji Supabase: {e}")


# --------------------- POSTGRESQL ---------------------
def setup_postgres_tables():
    try:
        pg_url = st.session_state.get("pg_url")
        engine = create_engine(pg_url)

        with engine.connect() as conn:
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS stocks_data (
                ticker TEXT,
                import_date TIMESTAMP,
                close FLOAT,
                volume FLOAT,
                sentiment FLOAT
            );
            """))
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS user_models (
                user_id TEXT,
                model_results JSONB,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """))
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS watchlist (
                user_id TEXT,
                ticker TEXT
            );
            """))
            conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alerts (
                user_id TEXT,
                ticker TEXT,
                target_price FLOAT,
                trigger TEXT
            );
            """))
            conn.commit()

        st.success("✅ PostgreSQL: tabele zostały utworzone automatycznie.")
    except Exception as e:
        st.warning(f"⚠️ Błąd przy inicjalizacji PostgreSQL: {e}")


# --------------------- MONGODB ---------------------
def setup_mongodb_collections():
    try:
        mongo_uri = st.session_state.get("mongo_uri")
        mongo_db_name = st.session_state.get("mongo_db")
        client = MongoClient(mongo_uri)
        db = client[mongo_db_name]

        collections = ["news_data", "sentiment_analysis"]
        for c in collections:
            if c not in db.list_collection_names():
                db.create_collection(c)

        st.success("✅ MongoDB: kolekcje utworzone automatycznie.")
    except Exception as e:
        st.warning(f"⚠️ Błąd przy inicjalizacji MongoDB: {e}")


# --------------------- CAŁOŚĆ ---------------------
def auto_initialize_all():
    st.info("🔄 Trwa automatyczna konfiguracja baz danych...")
    setup_supabase_tables()
    setup_postgres_tables()
    setup_mongodb_collections()
    st.success("🎯 Wszystkie bazy zostały poprawnie skonfigurowane.")
