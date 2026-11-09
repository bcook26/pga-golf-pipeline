import pandas as pd


def transform_stats_reference(
    stats_df: pd.DataFrame,
) -> pd.DataFrame:

    reference_df = (
        stats_df[
            [
                "stat_id",
                "stat_name",
            ]
        ]
        .dropna(
            subset=[
                "stat_id",
                "stat_name",
            ]
        )
        .drop_duplicates(
            subset=["stat_id"],
        )
        .sort_values(
            "stat_id",
        )
        .reset_index(drop=True)
    )

    return reference_df

def validate_stats_reference(
    stats_df: pd.DataFrame,
) -> None:

    conflicts = (
        stats_df
        .groupby("stat_id")["stat_name"]
        .nunique()
        .loc[lambda x: x > 1]
    )

    if not conflicts.empty:
        raise ValueError(
            "Found stat_ids with multiple stat_names: "
            f"{conflicts.index.tolist()}"
        )
