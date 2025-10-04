import pandas as pd

def convert_market_cap(value):
    if pd.isna(value):
        return None
    value = str(value).replace(",", "").strip()  # usuń przecinki i spacje
    try:
        if value.endswith('B'):
            return float(value[:-1]) * 1e9
        elif value.endswith('M'):
            return float(value[:-1]) * 1e6
        elif value.endswith('K'):
            return float(value[:-1]) * 1e3
        else:
            return float(value)
    except:
        return None

# przykładowe dane
df = pd.DataFrame({
    "Ticker": ["A"],
    "Company": ["Agilent Technologies Inc"],
    "Sector": ["Healthcare"],
    "Industry": ["Diagnostics & Research"],
    "Country": ["USA"],
    "Market Cap": ["35.26B"],
    "P/E": [29.17],
    "Price": [124.38],
    "Change": ["-1.24%"],
    "Volume": ["1,239,904"]
})

# konwersja Market Cap
df["market_cap"] = df["Market Cap"].apply(convert_market_cap)
df["Volume"] = df["Volume"].str.replace(",", "").astype(float)
df["Change"] = df["Change"].str.replace("%", "").astype(float)

# usuń starą kolumnę
df.drop(columns=["Market Cap"], inplace=True)

print(df)
