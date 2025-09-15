import os
import sys
import dotenv
from sqlalchemy import create_engine, text
import pandas as pd
import logging
from src.save_data import save_csv_to_db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

dotenv.load_dotenv()

logging.basicConfig(
    filename="../raports/database.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def get_engine():
    """Tworzy obiekt engine do bazy."""
    url = "postgresql://postgres:adomagala@127.0.0.1:5432/trading_analyzer"
    print(url)
    return create_engine(url)


def init_db_if_not_exists():
    """Tworzy tabelę if not exists"""
    engine = get_engine()
    ddl = """
    CREATE TABLE IF NOT EXISTS stocks_data (
    ticker VARCHAR(10),
    company VARCHAR(255),
    sector VARCHAR(255),
    industry VARCHAR(255),
    country VARCHAR(100),
    market_cap NUMERIC,
    p_e NUMERIC,
    eps_next_5y VARCHAR(10),
    perf_week VARCHAR(10),
    perf_month VARCHAR(10),
    fifty_two_week_high VARCHAR(10),
    fifty_two_week_low VARCHAR(10),
    rel_volume NUMERIC,
    volume INTEGER,
    price NUMERIC,
    change VARCHAR(10),
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))
    logging.info("Tabela stocks gotowa")


def read_from_db(table_name: str = "stocks_data") -> pd.DataFrame:
    """odczytuje i zwraca jako df"""
    engine = get_engine()
    df = pd.read_sql(f"SELECT * FROM {table_name}", engine)
    return df


if __name__ == "__main__":
    init_db_if_not_exists()
    save_csv_to_db("20250915")
