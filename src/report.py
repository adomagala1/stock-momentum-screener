import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from analyzer import analyze_stocks, top_gainers

def generate_report():
    """Generuje raport cenowy i zapisuje do pliku."""
    df = analyze_stocks()
    gainers = top_gainers(df)

    # histogram cen
    plt.figure(figsize=(10,6))
    sns.histplot(df["price"], bins=30)
    plt.title("Rozkład cen spółek w screenerze")
    plt.savefig("data/report_price_distribution.png")
    plt.close()

    # top gainers
    plt.figure(figsize=(12,6))
    sns.barplot(x="ticker", y="gap_to_high", data=gainers)
    plt.title("Spółki blisko 52W high")
    plt.xticks(rotation=45)
    plt.savefig("data/report_top_gainers.png")
    plt.close()

    print("Raporty wygenerowane.")


if __name__ == "__main__":
    generate_report()
