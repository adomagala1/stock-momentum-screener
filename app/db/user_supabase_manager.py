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
        saved_count = 0
        try:
            logging.info(f"Próbuję zapisać {len(df)} rekordów do {table_name}")
            st.info(f"Liczba rekordów próbujących się zapisać: {len(df)}")

            rename_map = {
                "Ticker": "ticker", "Company": "company", "Sector": "sector",
                "Industry": "industry", "Country": "country", "market_cap": "market_cap",
                "Market Cap": "market_cap", "P/E": "p_e", "Price": "price",
                "Change": "change", "Volume": "volume",
            }
            df = df.rename(columns=rename_map)
            df = df.loc[:, ~df.columns.duplicated()]

            expected_cols = [
                "ticker", "company", "sector", "industry", "country",
                "market_cap", "p_e", "price", "change", "volume"
            ]
            df = df[[c for c in expected_cols if c in df.columns]]

            for col in ["eps_next_5y", "perf_week", "perf_month",
                        "fifty_two_week_high", "fifty_two_week_low", "rel_volume"]:
                if col not in df.columns:
                    df[col] = None

            df["import_date"] = date.today().isoformat()

            for col in ["market_cap", "p_e", "price", "rel_volume", "volume"]:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(",", "", regex=False)
                    df[col] = df[col].str.replace("B", "e9", regex=False)
                    df[col] = df[col].str.replace("M", "e6", regex=False)
                    df[col] = df[col].str.replace("K", "e3", regex=False)
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                    df[col] = df[col].apply(lambda x: None if x is None or pd.isna(x) or np.isinf(x) else x)

            df = df.where(pd.notnull(df), None)

            data = df.to_dict(orient="records")
            logging.info(f"Liczba rekordów po czyszczeniu: {len(data)}")
            st.info(f"Liczba rekordów po czyszczeniu NaN/inf: {len(data)}")

            batch_size = 500
            for i in range(0, len(data), batch_size):
                chunk = data[i:i + batch_size]
                response = self.client.table(table_name).insert(chunk).execute()
                if hasattr(response, "error") and response.error:
                    logging.error(f"❌ Błąd Supabase: {response.error}")
                    st.error(f"❌ Błąd Supabase w batchu {i // batch_size + 1}: {response.error}")
                else:
                    saved_count += len(chunk)
                    logging.info(f"✅ Zapisano batch {i // batch_size + 1}, rekordy: {len(chunk)}")
                    st.success(f"✅ Zapisano batch {i // batch_size + 1}, rekordy: {len(chunk)}")

            logging.info(f"✅ Łącznie zapisano {saved_count} rekordów do {table_name}")
            st.success(f"✅ Łącznie zapisano {saved_count} rekordów do {table_name}")
            return saved_count

        except Exception as e:
            logging.exception(f"❌ Błąd podczas zapisu do Supabase: {e}")
            st.error(f"❌ Nie udało się zapisać żadnego rekordu. Szczegóły w logach: {e}")
            return saved_count


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
