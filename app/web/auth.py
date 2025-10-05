# app/web/auth.py

import streamlit as st
from .supabase_client import supabase

def login(email: str, password: str):
    """Logowanie użytkownika"""
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        user = res.user
        if user:
            st.session_state['user'] = {'email': user.email, 'id': user.id}
            # --------------------------
            st.success(f"✅ Zalogowano: {email}")
            return True
    except Exception as e:
        st.error("️Błąd logowania: Nieprawidłowy email lub hasło. Jeśli dopiero stworzyłeś konto, musisz potwierdzić na mailu")
    return False

def logout():
    """Wylogowanie użytkownika"""
    st.session_state.pop('user', None)
    st.session_state.pop('is_guest', None)
    try:
        supabase.auth.sign_out()
    except Exception as e:
        pass
    st.success("👋 Wylogowano")

def register(email: str, password: str):
    """Rejestracja nowego użytkownika"""
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        st.success(f"🎉 Utworzono konto dla {email}")
        st.info("Mail -> potwierdzic -> Mozesz sie zalogowac")
    except Exception as e:
        # Lepsza obsługa błędów, np. gdy użytkownik już istnieje
        if 'User already registered' in str(e):
            st.error("⚠️ Użytkownik z tym adresem email już istnieje.")
        else:
            st.error(f"⚠️ Błąd rejestracji: {e}")


