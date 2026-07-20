import pandas as pd

def clean_string_column(
    df: pd.DataFrame,
    column: str,
    default_value: str = "Not Available"
) -> pd.DataFrame:

    df[column] = (
        df[column]
        .astype("string")
        .str.strip()
        .replace("", default_value)
        .fillna(default_value)
        .str.title()
    )

    return df
