import numpy as np
import pandas as pd
import pytest
from database.postgres import to_records, upsert_dataframe
from pipeline.runner import plan_seasons, select_stat_players
from transform.stats import STATS_COLUMNS, clean_stats_frame, transform_stats
from transform.stats_reference import transform_stats_reference


def test_empty_extraction_yields_empty_typed_frames():
    stats = transform_stats(pd.DataFrame(), year=2026)
    assert list(stats.columns) == STATS_COLUMNS
    assert transform_stats_reference(stats).empty


def test_clean_stats_frame_coerces_and_dedupes():
    df = pd.DataFrame(
        {
            "player_id": ["1", "1", "1"],
            "player_name": ["A"] * 3,
            "season": [2026] * 3,
            "stat_id": ["s1", "s1", "s2"],
            "stat_name": ["x"] * 3,
            "stat_value": ["1.5", "-", "2"],
            "rank": ["3", None, "x"],
            "category": [None] * 3,
            "above_or_below": [None] * 3,
            "field_average": [None] * 3,
            "supporting_stat": [None] * 3,
            "supporting_value": [None] * 3,
        }
    )
    out = clean_stats_frame(df)
    assert len(out) == 2  # duplicate (1, 2026, s1) collapsed
    assert out["stat_value"].isna().iloc[0]  # "-" became NULL (kept last)
    assert out["rank"].isna().all()


def test_to_records_converts_nan_to_none():
    df = pd.DataFrame(
        {"a": [1, 2], "b": [np.nan, 3.0], "c": pd.array([None, 4], dtype="Int64")}
    )
    recs = to_records(df)
    assert recs[0]["b"] is None and recs[0]["c"] is None
    assert recs[1]["c"] == 4 and type(recs[1]["c"]) is int


def test_upsert_rejects_duplicate_keys():
    from sqlalchemy import Column, Integer, MetaData, Table

    table = Table("t", MetaData(), Column("k", Integer), Column("v", Integer))
    df = pd.DataFrame({"k": [1, 1], "v": [1, 2]})
    with pytest.raises(ValueError, match="duplicate"):
        upsert_dataframe(df, table, ["k"])


def test_plan_seasons():
    assert plan_seasons("incremental", 2026, None) == [2026]
    assert plan_seasons("backfill", 2026, None) == [2023, 2024, 2025, 2026]
    assert plan_seasons("backfill", 2026, [2025, 2024]) == [2024, 2025]
    with pytest.raises(ValueError):
        plan_seasons("nope", 2026, None)


def test_select_stat_players():
    df = pd.DataFrame(
        {
            "player_id": ["1", "2", "3", "4"],
            "is_active": [True, True, False, False],
            "primary_tour": ["PGA Tour", "Korn Ferry Tour", "PGA Tour", "PGA Tour"],
        }
    )
    # incremental: active PGA Tour + players already holding stats
    out = select_stat_players(df, "incremental", False, {"3"})
    assert out["player_id"].tolist() == ["1", "3"]
    # backfill / --all-players: everyone
    assert len(select_stat_players(df, "backfill", False, set())) == 4
    assert len(select_stat_players(df, "incremental", True, set())) == 4
