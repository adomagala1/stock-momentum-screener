"""
scraper.py
----------
Moduł do pobierania danych giełdowych z Finviz.
Wersja rozszerzona z logowaniem, retry i czyszczeniem danych.
"""
import os
import sys

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FINVIZ_URL

logging.basicConfig(
    filename="data/scraper.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_page(url: str) -> str:
    """Pobiera stronę z retry."""
    for i in range(3):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code == 200:
                return response.text
            logging.warning(f"Nieudane pobranie ({response.status_code}) próba {i + 1}")
        except Exception as e:
            logging.error(f"Błąd podczas pobierania: {e}")
        time.sleep(random.uniform(1, 3))
    raise ConnectionError("Nie udało się pobrać strony Finviz.")


def parse_table(html: str) -> pd.DataFrame:
    """Parsuje tabelę ze strony Finviz do DataFrame."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("tr", id="screener-table")

    if not table:
        raise ValueError("Nie znaleziono tabeli na stronie Finviz.")

    rows = table.find_all("tr")[1:]
    data = []
    for row in rows:
        cols = [col.get_text(strip=True) for col in row.find_all("td")]
        if cols:
            data.append(cols)

    df = pd.DataFrame(data)
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Czyści kolumny z %, Mld itp."""
    for col in df.columns:
        df[col] = df[col].str.replace("%", "", regex=False)
        df[col] = df[col].str.replace("M", "e6", regex=False)
        df[col] = df[col].str.replace("B", "e9", regex=False)
        df[col] = df[col].str.replace("K", "e3", regex=False)
    return df


def fetch_finviz_data() -> pd.DataFrame:
    """Główna funkcja: pobiera i zwraca dane z Finviz."""
    logging.info("Pobieranie danych z Finviz...")
    html = fetch_page(FINVIZ_URL)
    df_start = parse_table(html)
    df = clean_data(df_start)
    logging.info(f"Pobrano {len(df)} wierszy z Finviz")
    return df


if __name__ == "__main__":
    try:
        df = fetch_finviz_data()
        print(df.head())
        df.to_csv("data/finviz_latest.csv", index=False)
        logging.info("Dane zapisane do data/finviz_latest.csv")
    except Exception as e:
        logging.error(f"Błąd główny scraper.py: {e}")
