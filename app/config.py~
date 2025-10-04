import streamlit as st
from pymongo import MongoClient
import psycopg2
from supabase import create_client

# --- MongoDB ---
mongo_uri = st.secrets["mongo_uri"]
mongo_db = st.secrets["mongo_db"]
mongo_client = MongoClient(mongo_uri)
db = mongo_client[mongo_db]

# --- PostgreSQL ---
pg_user = st.secrets["pg_user"]
pg_password = st.secrets["pg_password"]
pg_host = st.secrets["pg_host"]
pg_port = st.secrets["pg_port"]
pg_db = st.secrets["pg_db"]

pg_conn = psycopg2.connect(
    user=pg_user,
    password=pg_password,
    host=pg_host,
    port=pg_port,
    database=pg_db
)

# --- Supabase ---
sb_url = st.secrets["sb_url"]
sb_api = st.secrets["sb_api"]
supabase = create_client(sb_url, sb_api)
