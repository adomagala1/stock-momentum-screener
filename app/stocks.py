import logging
import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from app.save_data import save_stocks_to_csv


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


def fetch_finviz_for_ticker(ticker: str) -> pd.DataFrame:
    """
    Pobiera dane dla pojedynczego tickera z Finviz.
    Zwraca DataFrame z jedną linią danych.
    """
    start_time = datetime.now()
    url = f"https://finviz.com/quote.ashx?t={ticker}"

    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table", class_="snapshot-table2")
    if not table:
        logging.warning(f"Nie znaleziono danych dla tickera {ticker}")
        return pd.DataFrame(columns=COLUMNS_NORMAL)

    cells = table.find_all("td")
    data_dict = {}
    for i in range(0, len(cells), 2):
        key = cells[i].get_text(strip=True)
        value = cells[i + 1].get_text(strip=True)
        data_dict[key] = value

    # Mapujemy dane Finviz do naszych kolumn
    mapped_data = {
        "Ticker": ticker,
        "Company": data_dict.get("Company", pd.NA),
        "Sector": data_dict.get("Sector", pd.NA),
        "Industry": data_dict.get("Industry", pd.NA),
        "Country": data_dict.get("Country", pd.NA),
        "Market Cap": data_dict.get("Market Cap", pd.NA),
        "P/E": data_dict.get("P/E", pd.NA),
        "Price": data_dict.get("Price", pd.NA),
        "Change": data_dict.get("Change", pd.NA),
        "Volume": data_dict.get("Volume", pd.NA)
    }

    df = pd.DataFrame([mapped_data], columns=COLUMNS_NORMAL)
    finish = datetime.now()
    logging.info(f"Pobrano dane dla {ticker}. Czas: {finish - start_time}")
    return df

def get_current_price(ticker: str) -> float | None:
    """
    Pobiera aktualną cenę danej spółki z Finviz (dostosowane do nowej struktury HTML)
    Zwraca float lub None, jeśli coś pójdzie nie tak.
    """
    try:
        url = f"https://finviz.com/quote.ashx?t={ticker.upper()}"
        response = requests.get(url, headers=HEADERS, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        price_tag = soup.find("strong", class_="quote-price_wrapper_price")
        if price_tag and price_tag.text:
            price_str = price_tag.text.strip().replace("$", "").replace(",", "")
            return float(price_str)

        price_cells = soup.find_all("td", class_="snapshot-td2")
        for cell in price_cells:
            if "$" in cell.text:
                return float(cell.text.replace("$", "").replace(",", ""))

        return None

    except Exception:
        return None


if __name__ == "__main__":
    df = fetch_finviz(max_companies=100, with_filters=False, get_only_tickers=False)
    save_stocks_to_csv(df, with_filters=False, get_only_tickers=False)
