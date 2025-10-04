import os
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import logging

# konfiguracja
FINVIZ_URL = "https://finviz.com/screener.ashx?v=111"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# logowanie
os.makedirs("data", exist_ok=True)
logging.basicConfig(
    filename="data/scraper.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def fetch_page(url: str) -> str:
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
    soup = BeautifulSoup(html, "html.parser")

    # Znajdujemy wszystkie tabele na stronie i wybieramy tę, która ma dane (często druga tabela)
    tables = soup.find_all("table")
    if len(tables) < 2:
        raise ValueError("Nie znaleziono tabeli z danymi.")

    table = tables[1]  # tabela z tickerami zwykle jest druga
    rows = table.find_all("tr")

    headers = [td.get_text(strip=True) for td in rows[0].find_all("td")]
    data = []
    for row in rows[1:]:
        cols = [td.get_text(strip=True) for td in row.find_all("td")]
        if cols and len(cols) == len(headers):
            data.append(cols)

    return pd.DataFrame(data, columns=headers)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        # upewniamy się, że kolumna jest stringiem
        df[col] = df[col].astype(str)

        # operacje na stringach
        try:
            df[col] = df[col].str.replace("%", "", regex=False)
            df[col] = df[col].str.replace("M", "e6", regex=False)
            df[col] = df[col].str.replace("B", "e9", regex=False)
            df[col] = df[col].str.replace("K", "e3", regex=False)
            df[col] = pd.to_numeric(df[col], errors="ignore")
        except AttributeError:
            # jeśli kolumna nie obsługuje .str (np. już jest DataFrame), pomijamy
            pass
    return df




def fetch_finviz_data() -> pd.DataFrame:
    logging.info("Pobieranie danych z Finviz...")
    html = fetch_page(FINVIZ_URL)
    df = parse_table(html)
    df = clean_data(df)
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
        print(f"Błąd: {e}")
