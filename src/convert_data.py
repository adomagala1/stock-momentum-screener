from helpers import get_exact_file
import pandas as pd


def csv_file_to_df(end_width: str, index_col="ticker") -> pd.DataFrame:
    file = get_exact_file(end_width)
    df = pd.read_csv(file, index_col=index_col)
    return df

