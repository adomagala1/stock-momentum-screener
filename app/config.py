import streamlit as st
from sqlalchemy import create_engine
from pymongo import MongoClient
from supabase import create_client

import streamlit as st

class Settings:
    # Mongo
    mongo_uri = st.secrets.get("mongo_uri")
    mongo_db = st.secrets.get("mongo_db", "stocks_db")

    # PostgreSQL / Supabase
    PG_HOST = st.secrets.get("pg_host")
    PG_USER = st.secrets.get("pg_user")
    PG_PASSWORD = st.secrets.get("pg_password")
    PG_DB = st.secrets.get("pg_db")

    # Supabase
    SB_URL = st.secrets.get("sb_url")
    SB_API = st.secrets.get("sb_api")
    SB_PASSWORD = st.secrets.get("sb_password")

settings = Settings()




# ----------------- DOMYŚLNE KONFIGURACJE (z secrets lub fallback) -----------------
MONGO_URI_DEFAULT = st.secrets.get("default_mongo_uri", "mongodb://localhost:27017/")
MONGO_DB_DEFAULT = st.secrets.get("default_mongo_db", "stocks_db")

PG_HOST_DEFAULT = st.secrets.get("default_pg_host", "yjyezqesjpuktrlxhxxx.supabase.co")
PG_USER_DEFAULT = st.secrets.get("default_pg_user", "postgres")
PG_PASSWORD_DEFAULT = st.secrets.get("default_pg_password", "Adrian9875GetMeAWork")
PG_DB_DEFAULT = st.secrets.get("default_pg_db", "trading_analyzer")

SB_URL_DEFAULT = st.secrets.get("default_sb_url")
SB_API_DEFAULT = st.secrets.get("default_sb_api")
SB_PASSWORD_DEFAULT = st.secrets.get("default_sb_password")

# ----------------- KONFIG Z SESSION STATE LUB DEFAULT -----------------
mongo_uri = st.session_state.get("mongo_uri", MONGO_URI_DEFAULT)
mongo_db_name = st.session_state.get("mongo_db", MONGO_DB_DEFAULT)

pg_host = st.session_state.get("pg_host", PG_HOST_DEFAULT)
pg_user = st.session_state.get("pg_user", PG_USER_DEFAULT)
pg_password = st.session_state.get("pg_password", PG_PASSWORD_DEFAULT)
pg_db = st.session_state.get("pg_db", PG_DB_DEFAULT)

sb_url = st.session_state.get("sb_url", SB_URL_DEFAULT)
sb_api = st.session_state.get("sb_api", SB_API_DEFAULT)
sb_password = st.session_state.get("sb_password", SB_PASSWORD_DEFAULT)


mongo_client = MongoClient(mongo_uri)
mongo_db = mongo_client[mongo_db_name]


pg_connection_string = f"postgresql://{pg_user}:{pg_password}@{pg_host}:5432/{pg_db}?sslmode=require"
engine = create_engine(pg_connection_string)


sb_client = None
if sb_url and sb_api:
    sb_client = create_client(sb_url, sb_api)

