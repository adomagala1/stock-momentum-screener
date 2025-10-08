import logging
import pandas as pd
import numpy as np
from datetime import date
from supabase import create_client, Client
import streamlit as st


class SupabaseHandler:
    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)

    def save_dataframe(self, df: pd.DataFrame, table_name: str = "stocks_data") -> int:
        """
        Zapisuje CZYSTY i PRZYGOTOWANY DataFrame do Supabase.
        Zakłada, że DataFrame ma już poprawne nazwy kolumn i typy danych.
        """
        # --- CAŁA LOGIKA CZYSZCZENIA ZOSTAŁA USUNIĘTA STĄD ---
        # Zakładamy, że DataFrame jest już idealnie przygotowany przez
        # funkcję `clean_and_transform_for_db` przed wywołaniem tej metody.

        if df.empty:
            logging.warning("Otrzymano pusty DataFrame do zapisu. Przerywam.")
            st.warning("Otrzymano pusty DataFrame, nic nie zostało zapisane.")
            return 0

        saved_count = 0
        try:
            st.info(f"Rozpoczynam zapis {len(df)} przygotowanych rekordów do tabeli '{table_name}'...")

            # Jedyna operacja: dodanie daty importu.
            # Ważne: df.copy() zapobiega ostrzeżeniom SettingWithCopyWarning.
            df_to_save = df.copy()
            df_to_save["import_date"] = date.today().isoformat()

            # Sprawdzenie, czy nie ma NaN tuż przed konwersją do JSON
            if df_to_save.isnull().values.any():
                st.error(
                    "Krytyczny błąd: Wykryto wartości NaN/None tuż przed konwersją do JSON, co nie powinno się zdarzyć.")
                st.write("Liczba wartości null w kolumnach:")
                st.write(df_to_save.isnull().sum())
                # Zamiana NaN na None jako ostatnia deska ratunku
                df_to_save = df_to_save.replace({np.nan: None})

            data = df_to_save.to_dict(orient="records")

            logging.info(f"Dane skonwertowane do formatu JSON. Rozmiar: {len(data)} rekordów.")

            # Zapis w paczkach (batching) - to jest dobra praktyka, zostawiamy
            batch_size = 500
            for i in range(0, len(data), batch_size):
                chunk = data[i:i + batch_size]
                response = self.client.table(table_name).insert(chunk).execute()

                # Poprawiona obsługa błędów Supabase v2
                if response.data:
                    saved_this_batch = len(response.data)
                    saved_count += saved_this_batch
                    logging.info(f"✅ Zapisano batch {i // batch_size + 1}, rekordy: {saved_this_batch}")
                else:  # To może być błąd, ale nie zawsze response.error jest ustawiony
                    logging.error(f"❌ Błąd Supabase lub pusty response w batchu {i // batch_size + 1}: {response}")
                    st.error(
                        f"❌ Błąd Supabase w batchu {i // batch_size + 1}. Sprawdź logi aplikacji oraz logi w panelu Supabase.")
                    # Przerywamy, jeśli jeden batch się nie powiedzie
                    break

            logging.info(f"✅ Zakończono proces zapisu. Łącznie zapisano {saved_count} rekordów.")
            return saved_count

        except Exception as e:
            # Ta sekcja złapie błąd "Out of range float values are not JSON compliant: nan" jeśli jakimś cudem jeszcze wystąpi
            logging.exception(f"❌ Krytyczny wyjątek podczas zapisu do Supabase: {e}")
            st.error(f"❌ Nie udało się zapisać żadnego rekordu. Szczegóły: {e}")
            return 0


def create_user(email: str, password: str, sb_url: str, sb_key: str) -> bool:
    """
    Tworzy nowego użytkownika w tabeli 'users' Supabase
    """
    sb = SupabaseHandler(sb_url, sb_key)
    try:
        response = sb.client.table("users").insert([{"email": email, "password": password}]).execute()
        if hasattr(response, "error") and response.error:
            logging.error(f"❌ Błąd przy tworzeniu użytkownika: {response.error}")
            st.error(f"❌ Błąd przy tworzeniu użytkownika: {response.error}")
            return False
        logging.info(f"✅ Utworzono użytkownika {email}")
        return True
    except Exception as e:
        logging.exception(f"❌ Wyjątek przy tworzeniu użytkownika: {e}")
        st.error(f"❌ Wyjątek przy tworzeniu użytkownika: {e}")
        return False


def get_users(sb_url: str, sb_key: str) -> pd.DataFrame:
    """
    Pobiera wszystkich użytkowników z tabeli 'users'
    """
    sb = SupabaseHandler(sb_url, sb_key)
    try:
        response = sb.client.table("users").select("*").execute()
        if hasattr(response, "error") and response.error:
            logging.error(f"❌ Błąd przy pobieraniu użytkowników: {response.error}")
            st.error(f"❌ Błąd przy pobieraniu użytkowników: {response.error}")
            return pd.DataFrame()
        data = response.data
        return pd.DataFrame(data)
    except Exception as e:
        logging.exception(f"❌ Wyjątek przy pobieraniu użytkowników: {e}")
        st.error(f"❌ Wyjątek przy pobieraniu użytkowników: {e}")
        return pd.DataFrame()


def clean_and_transform_for_db(df: pd.DataFrame) -> pd.DataFrame:
    """
    Kompleksowo czyści i transformuje DataFrame z Finviz do formatu bazodanowego.
    1. Standaryzuje nazwy kolumn (małe litery, podkreślniki).
    2. Usuwa znaki specjalne (B, M, %, ,) z wartości.
    3. Konwertuje kolumny na właściwe typy numeryczne, obsługując błędy.
    4. Zamienia wszystkie pozostałe NaN/NaT na None dla kompatybilności z JSON/SQL.
    """
    df_copy = df.copy()

    # --- 1. Standaryzacja nazw kolumn (kluczowe dla spójności z bazą danych!) ---
    # np. 'Market Cap' -> 'market_cap', 'P/E' -> 'p_e'
    original_columns = df_copy.columns.tolist()
    new_columns = [
        col.lower().replace(' ', '_').replace('.', '').replace('/', '_')
        for col in original_columns
    ]
    df_copy.columns = new_columns

    # Słownik kolumn do transformacji
    # Klucze to już nowe, czyste nazwy kolumn
    cols_to_process = {
        'market_cap': lambda x: str(x).replace('B', 'e9').replace('M', 'e6').replace('K', 'e3'),
        'p_e': lambda x: x,
        'price': lambda x: x,
        'change': lambda x: str(x).replace('%', ''),
        'volume': lambda x: str(x).replace(',', '')
    }

    # --- 2. Wstępne czyszczenie wartości tekstowych ---
    for col, clean_func in cols_to_process.items():
        if col in df_copy.columns:
            # Używamy .loc, aby uniknąć SettingWithCopyWarning
            df_copy.loc[:, col] = df_copy[col].apply(clean_func)

    # Lista kolumn, które mają być liczbami
    numeric_cols = ['market_cap', 'p_e', 'price', 'change', 'volume']

    # --- 3. Konwersja na typy numeryczne (NAJWAŻNIEJSZY KROK) ---
    # errors='coerce' zamieni wszystko, co nie jest liczbą (np. myślnik '-') na NaN
    for col in numeric_cols:
        if col in df_copy.columns:
            df_copy.loc[:, col] = pd.to_numeric(df_copy[col], errors='coerce')

    # Dodatkowa transformacja dla analizy: zmiana procentowa jako ułamek
    if 'change' in df_copy.columns:
        df_copy.loc[:, 'change'] = df_copy['change'] / 100.0

    # --- 4. Ostateczna zamiana NaN na None (rozwiązuje problem z JSON) ---
    # To łapie wszystkie NaN stworzone przez 'coerce' w kroku 3
    df_final = df_copy.replace({np.nan: None, pd.NaT: None})

    return df_final
