# app/web/auth.py

import streamlit as st
from .supabase_client import supabase

def login(email, password):
    user = supabase.auth.sign_in_with_password({"email": email, "password": password})
    if user.user:
        st.session_state['user'] = user.user
        st.session_state['access_token'] = user.session.access_token
        st.success(f"Zalogowano: {user.user.email}")
        return True
    else:
        st.error("Błąd logowania")
        return False

def check_login():
    if 'access_token' in st.session_state:
        user = supabase.auth.get_user(st.session_state['access_token'])
        if user.user:
            st.session_state['user'] = user.user
            return True
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


