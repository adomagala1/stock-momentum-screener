import logging
import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from save_data import save_stocks_to_csv

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    filename="logs/stock_scraper.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}

URL_DEFAULT = "https://finviz.com/screener.ashx?v=111"
URL_FILTERED = (
    "https://finviz.com/screener.ashx?v=152&f=cap_mid,exch_nasd,sh_avgvol_o500,"
    "sh_price_o5,sh_relvol_o1.5&c=1,2,3,4,5,6,7,20,42,43,57,58,64,67,65,66"
)

COLUMNS_NORMAL = [
    "No", "Ticker", "Company", "Sector", "Industry", "Country",
    "Market Cap", "P/E", "Price", "Change", "Volume"
]

COLUMNS_FILTERED = [
    "Ticker", "Company", "Sector", "Industry", "Country", "Market Cap", "P/E",
    "EPS next 5Y", "Perf Week", "Perf Month", "52w High", "52w Low",
    "Rel Vol", "Volume", "Price", "Change"
]


def fetch_finviz(max_companies: int = 10, get_only_tickers: bool = False, with_filters: bool = False) -> pd.DataFrame:
    url = URL_FILTERED if with_filters else URL_DEFAULT
    start_time = datetime.now()
    all_data = []
    start = 1
    companies_fetched = 0
    unlimited = max_companies is None or max_companies <= 0
    columns = ["No", "Ticker"] if get_only_tickers else (COLUMNS_FILTERED if with_filters else COLUMNS_NORMAL)

    while True:
        if not unlimited and companies_fetched >= max_companies:
            break

        paged_url = url + f"&r={start}"
        response = requests.get(paged_url, headers=HEADERS)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.find_all("tr", class_="styled-row")
        if not rows:
            break

        for row in rows:
            cols = row.find_all("td")
            row_data = [col.get_text(strip=True) for col in cols]
            if get_only_tickers:
                all_data.append([row_data[0], row_data[1]])  # numer + ticker
            else:
                all_data.append(row_data[:len(columns)])
            companies_fetched += 1
            if not unlimited and companies_fetched >= max_companies:
                break
        start += 20

    df = pd.DataFrame(all_data, columns=columns)
    df.fillna(pd.NA, inplace=True)
    finish = datetime.now()
    logging.info(f"Pobrano {len(df)} spółek. Czas: {finish - start_time}")
    return df

if __name__ == "__main__":
    df = fetch_finviz(max_companies=100, with_filters=False, get_only_tickers=False)
    save_stocks_to_csv(df, with_filters=False, get_only_tickers=False)
