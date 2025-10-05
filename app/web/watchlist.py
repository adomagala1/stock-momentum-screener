# app/web/watchlist.py

import streamlit as st
from .supabase_client import supabase


def get_watchlist(user_id: str):
    """Pobiera watchlistę dla danego użytkownika."""
    # Zabezpieczenie na wypadek, gdyby user_id było None
    if not user_id: return []
    try:
        res = supabase.table("watchlist").select("id, ticker").eq("user_id", user_id).order("ticker").execute()
        return res.data or []
    except Exception as e:
        st.error(f"Błąd podczas ładowania watchlisty: {e}")
        return []


def add_to_watchlist(user_id: str, ticker: str):
    """Dodaje ticker do watchlisty, unikając duplikatów."""
    try:
        exists = supabase.table("watchlist").select("id").eq("user_id", user_id).eq("ticker", ticker.upper()).execute()
        if not exists.data:
            supabase.table("watchlist").insert({"user_id": user_id, "ticker": ticker.upper()}).execute()
            st.toast(f"✅ Dodano {ticker} do obserwowanych!")
        else:
            st.toast(f"ℹ️ {ticker} jest już na Twojej liście.")
    except Exception as e:
        st.error(f"Błąd podczas dodawania do watchlisty: {e}")


def remove_from_watchlist(item_id: int):
    """Usuwa ticker z watchlisty na podstawie jego ID w bazie."""
    try:
        supabase.table("watchlist").delete().eq("id", item_id).execute()
        st.toast("🗑️ Usunięto z obserwowanych.")
    except Exception as e:
        st.error(f"Błąd podczas usuwania z watchlisty: {e}")
