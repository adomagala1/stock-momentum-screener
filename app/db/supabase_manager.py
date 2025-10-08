# app/db/supabase_manager.py
import streamlit as st

from sqlalchemy import text
from app.db.mongodb import news_col, update_news_for_ticker
from app.web.supabase_client import supabase
import logging


logging.basicConfig(
    level=logging.INFO,
    filename="logs/db_manager.log",
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def get_user_by_email(email: str):
    """Zwraca użytkownika z Supabase na podstawie emaila"""
    resp = supabase.table("users").select("*").eq("email", email).execute()
    return resp.data[0] if resp.data else None


def get_user_watchlist(user_id: str) -> list:
    """Zwraca tickery z watchlisty użytkownika"""
    resp = supabase.table("watchlist").select("ticker").eq("user_id", user_id).execute()
    return [r["ticker"] for r in resp.data] if resp.data else []


def add_to_watchlist(user_id: str, ticker: str):
    """Dodaje ticker do watchlisty użytkownika"""
    supabase.table("watchlist").insert({"user_id": user_id, "ticker": ticker}).execute()
    logging.info(f"[WATCHLIST] Dodano {ticker} dla użytkownika {user_id}")


def remove_from_watchlist(user_id: str, ticker: str):
    """Usuwa ticker z watchlisty"""
    supabase.table("watchlist").delete().eq("user_id", user_id).eq("ticker", ticker).execute()
    logging.info(f"[WATCHLIST] Usunięto {ticker} z watchlisty użytkownika {user_id}")

