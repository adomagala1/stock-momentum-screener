import logging
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings
from save_data import convert_market_cap

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
    from app.database import get_engine
    from app.helpers import get_exact_file
    try:
        csv_file = get_exact_file(end_width, get_only_tickers, with_filters)
        df = pd.read_csv(csv_file)
        df.columns = (
            df.columns.str.strip()
            .str.lower()
            .str.replace(" ", "_")
            .str.replace("%", "_perc")
            .str.replace("^", "", regex=True)
        )
        df = df.rename(columns={
            "52w_high": "fifty_two_week_high",
            "52w_low": "fifty_two_week_low",
            "rel_vol": "rel_volume",
            "eps_next_5y": "eps_next_5y",
            "p/e": "p_e"
        })
        df["market_cap"] = df["market_cap"].apply(convert_market_cap)
        df["price"] = pd.to_numeric(df["price"].astype(str).str.replace(",", "", regex=False), errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"].astype(str).str.replace(",", "", regex=False), errors="coerce")
        df["change"] = df["change"].replace("-", pd.NA)
        df["import_date"] = datetime.strptime(end_width, "%Y%m%d").date()

        engine = get_engine()
        logging.info(f"DataFrame przed zapisem:\n{df.head()}")
        logging.info(f"Liczba wierszy: {len(df)}")
        df.to_sql(table_name, engine, if_exists="append", index=False)
        logging.info(f"Zapisano {len(df)} rekordów do {table_name}")
    except Exception as e:
        logging.error(f"Błąd podczas zapisywania do bazy danych: {e}")
