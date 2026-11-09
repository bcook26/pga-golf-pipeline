import pandas as pd
from extract.base import GolfDataSource


def extract_players(source: GolfDataSource) -> pd.DataFrame:
    """Fetch the raw player directory from the given data source."""
    return source.fetch_players()
