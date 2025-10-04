import logging
import os
from datetime import date
import pandas as pd
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
from app.database import get_engine
from app.config import settings
from app.helpers import get_exact_file

logging.basicConfig(
    level=logging.INFO,
    filename="logs/postgresql.log",
    format="%(asctime)s [%(levelname)s] %(message)s"
)

DATABASE_URL = (
    f"postgresql://{settings.pg_user}:{settings.pg_password}@127.0.0.1:{settings.pg_port}/{settings.pg_db}"
)
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def save_csv_to_db(get_only_tickers: bool, with_filters: bool, end_width: str, table_name: str = "stocks_data"):
    try:
        logging.info(f"Zapisywanie do {table_name}, end_width: {end_width}")

        # Pobranie pliku CSV
        csv_file = get_exact_file(end_width, get_only_tickers, with_filters, file_type="stocks")
        logging.info(f"Szukam pliku: {csv_file}")
        if not os.path.exists(csv_file):
            logging.error(f"Plik {csv_file} nie istnieje!")
            return

        # Próba wczytania CSV
        try:
            df = pd.read_csv(csv_file, encoding="utf-8", on_bad_lines="skip")
        except UnicodeDecodeError:
            df = pd.read_csv(csv_file, encoding="latin-1", on_bad_lines="skip")

        logging.info(f"Kolumny wczytane z CSV: {df.columns.tolist()}")

        # Normalizacja kolumn
        rename_map = {
            "Ticker": "ticker",
            "Company": "company",
            "Sector": "sector",
            "Industry": "industry",
            "Country": "country",
            "market_cap": "market_cap",
            "Market Cap": "market_cap",  # różne warianty
            "P/E": "p_e",
            "Price": "price",
            "Change": "change",
            "Volume": "volume",
        }
        df = df.rename(columns=rename_map)

        # Usuwanie duplikatów nazw kolumn
        df = df.loc[:, ~df.columns.duplicated()]
        logging.info(f"Kolumny po czyszczeniu: {df.columns.tolist()}")

        # Zostaw tylko kolumny istotne
        expected_cols = [
            "ticker", "company", "sector", "industry", "country",
            "market_cap", "p_e", "price", "change", "volume"
        ]
        df = df[[c for c in expected_cols if c in df.columns]]

        # Dodaj brakujące kolumny wymagane przez DB
        df["eps_next_5y"] = None
        df["perf_week"] = None
        df["perf_month"] = None
        df["fifty_two_week_high"] = None
        df["fifty_two_week_low"] = None
        df["rel_volume"] = None

        # Dodaj kolumnę import_date
        df["import_date"] = date.today()

        # Konwersje liczbowe
        for col in ["market_cap", "p_e", "price", "rel_volume"]:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(",", "", regex=False)
                    .str.replace("B", "e9", regex=False)
                    .str.replace("M", "e6", regex=False)
                    .str.replace("K", "e3", regex=False)
                )
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "volume" in df.columns:
            df["volume"] = (
                df["volume"]
                .astype(str)
                .str.replace(",", "", regex=False)
            )
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)

        # Zapis do bazy
        engine = get_engine()
        with engine.begin() as conn:
            for _, row in df.iterrows():
                sql = text(f"""
                    INSERT INTO {table_name} 
                    (ticker, company, sector, industry, country, market_cap, p_e,
                     eps_next_5y, perf_week, perf_month, fifty_two_week_high, fifty_two_week_low,
                     rel_volume, volume, price, change, import_date)
                    VALUES (:ticker, :company, :sector, :industry, :country, :market_cap, :p_e,
                            :eps_next_5y, :perf_week, :perf_month, :fifty_two_week_high, :fifty_two_week_low,
                            :rel_volume, :volume, :price, :change, :import_date)
                    ON CONFLICT (ticker, import_date) DO NOTHING
                """)
                conn.execute(sql, row.to_dict())

        logging.info(f"Dane z {csv_file} zapisane do {table_name}")

    except Exception as e:
        logging.exception(f"Błąd podczas zapisu do bazy: {e}")


if __name__ == "__main__":
    save_csv_to_db(get_only_tickers=False, with_filters=False, end_width="20251002")
