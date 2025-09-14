"""
database.py
-----------
Obsługa bazy danych PostgreSQL (SQLAlchemy).
"""
import os
import sys
import dotenv
from sqlalchemy import create_engine, text
import pandas as pd
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

dotenv.load_dotenv()

logging.basicConfig(
    filename="../raports/database.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def get_engine():
    """Tworzy obiekt engine do bazy."""
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST")

    url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
    return create_engine(url)


def init_db():
    """Tworzy tabelę jeśli nie istnieje."""
    engine = get_engine()
    ddl = """
    CREATE TABLE IF NOT EXISTS stocks (
        id SERIAL PRIMARY KEY,
        ticker VARCHAR(10),
        company VARCHAR(255),
        sector VARCHAR(255),
        price FLOAT,
        volume BIGINT,
        rel_volume FLOAT,
        fifty_two_week_high FLOAT,
        created_at TIMESTAMP DEFAULT NOW()
    );
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    logging.info("Tabela stocks gotowa.")


def save_to_db(df: pd.DataFrame, table_name: str = "stocks"):
    """Zapisuje DataFrame do bazy."""
    engine = get_engine()
    df.to_sql(table_name, engine, if_exists="append", index=False)
    logging.info(f"Zapisano {len(df)} rekordów do {table_name}")


def read_from_db(table_name: str = "stocks") -> pd.DataFrame:
    """Odczytuje dane z bazy do DataFrame."""
    engine = get_engine()
    df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
    return df


if __name__ == "__main__":
    init_db()
    print("Baza gotowa do pracy.")
