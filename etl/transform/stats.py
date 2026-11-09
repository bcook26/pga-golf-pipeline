import pandas as pd


def normalize_category(category) -> str | None:

    if category is None:
        return None

    if isinstance(category, list):
        return ", ".join(category)

    return str(category)


def transform_stats(
    extracted_stats: pd.DataFrame,
    year: int,
) -> pd.DataFrame:

    if extracted_stats.empty:
        return pd.DataFrame()

    rows = []

    for _, player in extracted_stats.iterrows():

        player_id = player["player_id"]
        player_name = player["player_name"]
        stats_data = player["raw_stats"]

        if stats_data is None:
            continue

        for stat in stats_data.get("stats", []):

            supporting_stat = stat.get(
                "supportingStat"
            )

            supporting_value = stat.get(
                "supportingValue"
            )

            rows.append(
                {
                    "player_id": player_id,
                    "player_name": player_name,
                    "season": year,
                    "stat_id": stat.get("statId"),
                    "stat_name": stat.get("title"),
                    "stat_value": stat.get("value"),
                    "rank": stat.get("rank"),
                    "category": normalize_category(
                        stat.get("category")
                    ),
                    "above_or_below": stat.get(
                        "aboveOrBelow"
                    ),
                    "field_average": stat.get(
                        "fieldAverage"
                    ),
                    "supporting_stat": (
                        supporting_stat.get("value")
                        if isinstance(
                            supporting_stat,
                            dict,
                        )
                        else None
                    ),
                    "supporting_value": (
                        supporting_value.get("value")
                        if isinstance(
                            supporting_value,
                            dict,
                        )
                        else None
                    ),
                }
            )

    return pd.DataFrame(
        rows,
        columns=[
            "player_id",
            "player_name",
            "season",
            "stat_id",
            "stat_name",
            "stat_value",
            "rank",
            "category",
            "above_or_below",
            "field_average",
            "supporting_stat",
            "supporting_value",
        ],
    )
