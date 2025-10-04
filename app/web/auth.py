# app/web/auth.py

import streamlit as st
from .supabase_client import supabase  # <-- ZMIANA: Import klienta

def login(email: str, password: str):
    """Logowanie użytkownika"""
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user = res.user
        if user:
            # Przechowujemy cały obiekt użytkownika dla łatwiejszego dostępu
            st.session_state['user'] = user
            st.success(f"✅ Zalogowano: {email}")
            return True
    except Exception as e:
        st.error(f"⚠️ Błąd logowania: {e}")
    return False

def logout():
    """Wylogowanie użytkownika"""
    if 'user' in st.session_state:
        del st.session_state['user']
    # Wywołanie sign_out() jest opcjonalne, ponieważ sesja jest zarządzana tokenem JWT
    # ale to dobra praktyka do unieważnienia tokenów po stronie serwera
    supabase.auth.sign_out()
    st.success("👋 Wylogowano")

def register(email: str, password: str):
    """Rejestracja nowego użytkownika"""
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        if res.user:
            st.success(f"🎉 Utworzono konto: {email}. Sprawdź email, aby potwierdzić rejestrację.")
        else:
            st.error("❌ Rejestracja nie powiodła się. Użytkownik może już istnieć.")
    except Exception as e:
        st.error(f"⚠️ Błąd rejestracji: {e}")