import pandas as pd


def breakout_alert(df: pd.DataFrame) -> pd.DataFrame:
    """Zwraca spółki blisko 52W high."""
    return df[df["price"] >= df["fifty_two_week_high"] * 0.98]


def volume_alert(df: pd.DataFrame) -> pd.DataFrame:
    """Zwraca spółki z nagłym wolumenem."""
    return df[df["rel_volume"] >= 2]


def combined_alerts(df: pd.DataFrame) -> pd.DataFrame:
    """Łączy breakout i volume alerty."""
    breakout = breakout_alert(df)
    volume = volume_alert(df)
    return pd.concat([breakout, volume]).drop_duplicates()


if __name__ == "__main__":
    import analyzer

    df = analyzer.analyze_stocks()
    alerts = combined_alerts(df)
    print("ALERTY:")
    print(alerts)
