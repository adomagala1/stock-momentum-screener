from stocks import get_current_price

tickers = ["AAPL", "TSLA", "NVDA"]

for t in tickers:
    price = get_current_price(t)
    if price is not None:
        print(f"{t}: ${price}")
    else:
        print(f"{t}: nie ma")
