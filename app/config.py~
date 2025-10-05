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


mongo_uri = settings.mongo_uri
mongo_db_name = settings.mongo_db

pg_user = settings.PG_USER
pg_password = settings.PG_PASSWORD
pg_host = settings.PG_HOST
pg_db = settings.PG_DB

sb_url = settings.SB_URL
sb_api = settings.SB_API

mongo_client = MongoClient(mongo_uri)
mongo_db = mongo_client[mongo_db_name]


pg_connection_string = f"postgresql://{pg_user}:{pg_password}@{pg_host}:5432/{pg_db}?sslmode=require"
engine = create_engine(pg_connection_string)


sb_client = None
if sb_url and sb_api:
    sb_client = create_client(sb_url, sb_api)

