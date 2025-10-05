# app/web/alerts.py

import streamlit as st
from .supabase_client import supabase

def get_alerts(user_id: str):
    """Pobiera wszystkie alerty dla danego użytkownika."""
    if not user_id: return []
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
            # Poprawiona logika - przekazujemy None bezpośrednio jeśli wartość to None lub 0
            "threshold_high": high if high else None,
            "threshold_low": low if low else None
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