import streamlit as st
from .supabase_client import supabase


def login(email, password):
    """Logowanie użytkownika"""
    try:
        user = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if user.user:
            st.session_state['user'] = user.user
            st.session_state['access_token'] = user.session.access_token
            st.session_state['refresh_token'] = user.session.refresh_token

            # ✅ Zapisz tokeny w query params (trwałe między refreshami)
            st.query_params.update({
                "access_token": user.session.access_token,
                "refresh_token": user.session.refresh_token
            })

            st.success(f"✅ Zalogowano jako {user.user.email}")
            return True
        else:
            st.error("❌ Błąd logowania")
            return False
    except Exception as e:
        st.error(f"⚠️ Błąd logowania: {e}")
        return False


def check_login():
    """Sprawdza czy użytkownik jest zalogowany (również po refreshu)"""
    # 1️⃣ Jeśli już zalogowany
    if 'access_token' in st.session_state:
        try:
            user = supabase.auth.get_user(st.session_state['access_token'])
            if user.user:
                st.session_state['user'] = user.user
                return True
        except Exception:
            pass

    # 2️⃣ Jeśli nie — sprawdź parametry URL (query params)
    access_token = st.query_params.get("access_token")
    refresh_token = st.query_params.get("refresh_token")

    if access_token:
        try:
            user = supabase.auth.get_user(access_token)
            if user.user:
                st.session_state['user'] = user.user
                st.session_state['access_token'] = access_token
                st.session_state['refresh_token'] = refresh_token
                return True
        except Exception as e:
            if "Session from session_id claim" in str(e) and refresh_token:
                # 🔁 Token wygasł — spróbuj odświeżyć sesję
                try:
                    new_session = supabase.auth.refresh_session(refresh_token)
                    st.session_state['user'] = new_session.user
                    st.session_state['access_token'] = new_session.session.access_token
                    st.session_state['refresh_token'] = new_session.session.refresh_token

                    # ✅ Aktualizacja tokenów w URL
                    st.query_params.update({
                        "access_token": new_session.session.access_token,
                        "refresh_token": new_session.session.refresh_token
                    })

                    return True
                except Exception:
                    st.warning("Sesja wygasła — zaloguj się ponownie.")
                    logout()
                    return False

    return False


def logout():
    """Wylogowanie użytkownika"""
    try:
        supabase.auth.sign_out()
    except Exception:
        pass

    # 🧹 Wyczyść sesję i URL
    for key in ['user', 'access_token', 'refresh_token', 'is_guest']:
        st.session_state.pop(key, None)

    st.query_params.clear()  # usuń tokeny z adresu
    st.success("👋 Wylogowano pomyślnie")


def register(email, password):
    """Rejestracja nowego użytkownika"""
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        st.success(f"🎉 Konto utworzone dla {email}")
        st.info("📧 Sprawdź maila i potwierdź konto przed logowaniem.")
    except Exception as e:
        if 'User already registered' in str(e):
            st.warning("⚠️ Użytkownik z tym adresem email już istnieje.")
        else:
            st.error(f"⚠️ Błąd rejestracji: {e}")
