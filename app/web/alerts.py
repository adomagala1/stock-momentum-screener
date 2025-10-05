# app/web/alerts.py

import streamlit as st
from .supabase_client import supabase
from app.stocks import get_current_price

def get_alerts(user_id: str):
    """Pobiera wszystkie alerty dla danego użytkownika."""
    try:
        res = supabase.table("alerts").select("*").eq("user_id", user_id).order("ticker").execute()
        return res.data or []
    except Exception as e:
        st.error(f"Błąd podczas ładowania alertów: {e}")
        return []

def add_alert(user_id, ticker, high, low):
    """Dodaje nowy alert cenowy."""
    try:
        supabase.table("alerts").insert({
            "user_id": user_id,
            "ticker": ticker.upper(),
            "threshold_high": high if high > 0 else None,
            "threshold_low": low if low > 0 else None
        }).execute()
        st.success(f"🔔 Ustawiono alert dla {ticker}!")
    except Exception as e:
        st.error(f"Błąd podczas dodawania alertu: {e}")

def remove_alert(alert_id: int):
    """Usuwa alert na podstawie jego ID."""
    try:
        supabase.table("alerts").delete().eq("id", alert_id).execute()
        st.toast("🗑️ Usunięto alert.")
    except Exception as e:
        st.error(f"Błąd podczas usuwania alertu: {e}")


def check_price(ticker: str):
    """Pobiera aktualne ceny dla podanego ticker'a."""
    try:
        price = get_current_price(ticker)
        return price
    except Exception as e:
        st.error(f"Błąd podczas pobierania ceny: {ticker} {e} alerts.py")
        return None