import pandas as pd
from database import read_from_db

def analyze_stocks(table_name="stocks") -> pd.DataFrame:
    """
    Zwraca spółki, które spełniają podstawowe kryteria momentum.
    """
    df = read_from_db(table_name)

    # filtr: cena > 10, wolumen > 500k, rel vol > 1.5
    filtered = df[
        (df["price"] > 10) &
        (df["volume"] > 500_000) &
        (df["rel_volume"] > 1.5)
    ]

    return filtered


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
