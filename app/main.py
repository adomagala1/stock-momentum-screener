import pandas as pd

from app.save_data import save_csv
from app.stock_scraper import fetch_all_finviz
from app.scrape_news import fetch_news_for_ticker
import logging

URL = "https://finviz.com/screener.ashx?v=111&f=exch_nasd"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}


logging.basicConfig(
    filename="../raports/main.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


if __name__ == "__main__":
    df = fetch_all_finviz(URL)
    save_csv(df)
    tickers_to_scrape_news = ["AAPL"]
    ALL = []
    for ticker in tickers_to_scrape_news:
        news_df = fetch_news_for_ticker(ticker)
        if not news_df.empty:
            ALL.append(news_df)
        else:
            logging.info(f"Brak wyników dla {ticker}")

    if ALL:
        final = pd.concat(ALL, ignore_index=True)
        print(final.values)
    else:
        print("Brak artykułów dla podanych tickerów.")
