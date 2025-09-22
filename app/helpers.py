import glob
import logging
import os


def get_exact_file(end_width: str, get_only_tickers, with_filters) -> str:
    filename_suffix = {
        # tylko tickery wszystkich (na dole)
        (True, False): f"finviz_tickers_{end_width}.csv",
        # wszystkie spolki (na dole)
        (False, False): f"finviz_stocks_{end_width}.csv",
        # filtry (na dle)
        (False, True): f"finviz_filtered_stocks_{end_width}.csv",
        # tickery + filtry (na dole)
        (True, True): f"finviz_filtered_tickers_{end_width}.csv"
    }
    pattern = os.path.abspath(os.path.join("data", filename_suffix.get((get_only_tickers, with_filters))))
    logging.info(pattern)
    files = glob.glob(pattern)

    if not files:
        raise FileNotFoundError(f"Brak pliku z koncowka '{end_width}' oraz sciezka abs {os.path.abspath(pattern)}")

    file = files[0]

    return file
