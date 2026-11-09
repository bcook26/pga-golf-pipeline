import re

import pandas as pd


def normalize_category(category) -> str | None:

    if category is None:
        return None

    if isinstance(category, list):
        return ", ".join(category)

    return str(category)


def clean_string_column(
    df: pd.DataFrame, column: str, default_value: str = "Not Available"
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


def create_player_slug(name):
    """Generate player name in format - first-last for reference in stats.py"""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return slug
