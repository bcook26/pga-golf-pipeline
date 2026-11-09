import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from database.connection import engine
from database.tables import tables

sql_engine = engine()

players_table, player_stats_table, stats_reference_table = tables(sql_engine)


# -------------------------
# Players UPSERT
# -------------------------

def upsert_players(
    df: pd.DataFrame,
) -> None:

    if df.empty:
        print("No player data to load.")
        return

    records = df.to_dict(
        orient="records",
    )

    stmt = insert(
        players_table,
    ).values(records)

    stmt = stmt.on_conflict_do_update(
        index_elements=["player_id"],
        set_={
            "display_name": stmt.excluded.display_name,
            "is_active": stmt.excluded.is_active,
            "country": stmt.excluded.country,
            "player_bio": stmt.excluded.player_bio,
            "primary_tour": stmt.excluded.primary_tour,
        },
    )

    with sql_engine.begin() as conn:
        conn.execute(stmt)

    print(
        f"Upserted {len(df)} players."
    )


# -------------------------
# Player Stats UPSERT
# -------------------------

def upsert_player_stats(
    df: pd.DataFrame,
    chunksize: int = 1000,
) -> None:

    if df.empty:
        print("No player stats to load.")
        return

    total_rows = len(df)

    with sql_engine.begin() as conn:

        for start in range(
            0,
            total_rows,
            chunksize,
        ):

            chunk = df.iloc[
                start:start + chunksize
            ]

            records = chunk.to_dict(
                orient="records",
            )

            stmt = insert(
                player_stats_table,
            ).values(records)

            stmt = stmt.on_conflict_do_update(
                index_elements=[
                    "player_id",
                    "season",
                    "stat_id",
                ],
                set_={
                    "player_name": stmt.excluded.player_name,
                    "stat_name": stmt.excluded.stat_name,
                    "stat_value": stmt.excluded.stat_value,
                    "rank": stmt.excluded.rank,
                    "category": stmt.excluded.category,
                    "above_or_below": stmt.excluded.above_or_below,
                    "field_average": stmt.excluded.field_average,
                    "supporting_stat": stmt.excluded.supporting_stat,
                    "supporting_value": stmt.excluded.supporting_value,
                },
            )

            conn.execute(stmt)

            print(
                f"Upserted "
                f"{min(start + chunksize, total_rows)} "
                f"of {total_rows} stat rows."
            )


# -------------------------
# Stats Reference UPSERT
# -------------------------

def upsert_stats_reference(
    df: pd.DataFrame,
) -> None:

    if df.empty:
        print("No stats reference data to load.")
        return

    records = df.to_dict(
        orient="records",
    )

    stmt = insert(
        stats_reference_table,
    ).values(records)

    stmt = stmt.on_conflict_do_update(
        index_elements=["stat_id"],
        set_={
            "stat_name": stmt.excluded.stat_name,
        },
    )

    with sql_engine.begin() as conn:
        conn.execute(stmt)

    print(
        f"Upserted {len(df)} stat reference records."
    )
