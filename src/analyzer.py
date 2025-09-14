import glob
import logging
import os.path

import pandas as pd
from database import read_from_db


def get_exact_file(end_width: str) -> str:
    pattern = f"data/finviz_stocks_*{end_width}.csv"
    logging.info(pattern)
    files = glob.glob(pattern)

    if not files:
        raise FileNotFoundError(f"Brak pliku z koncowka '{end_width}'")

    file = files[0]

    return file


def csv_file_to_df(end_width: str, index_col="Ticker") -> pd.DataFrame:
    file = get_exact_file(end_width)
    df = pd.read_csv(file, index_col=index_col)
    return df


def analyze_from_csv(end_width: str, operation: int) -> pd.DataFrame:
    file = get_exact_file(end_width)

    #
    if operation == 1:
        pass




def top_gainers(df: pd.DataFrame, n=10):
    """Zwraca top n spółek z największym wzrostem do 52W high."""
    df["gap_to_high"] = (df["fifty_two_week_high"] - df["price"]) / df["fifty_two_week_high"] * 100
    return df.sort_values("gap_to_high").head(n)


if __name__ == "__main__":
    df = analyze_stocks()
    print("Spółki spełniające kryteria:")
    print(df.head())

    print("\nTop 10 rakiet blisko ATH:")
    print(top_gainers(df))
