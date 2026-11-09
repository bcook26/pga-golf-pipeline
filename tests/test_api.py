"""API tests against a real Postgres (compose DB locally, service in CI).

Each test seeds fixture rows inside a transaction that is rolled back, so the
tests never read or modify real warehouse data. Skipped if no DB is reachable.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from app.config import get_settings
from app.db import get_conn, get_engine
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import Connection, text

SEASON_A, SEASON_B = 1998, 1999  # far from any real season


@pytest.fixture()
def conn() -> Iterator[Connection]:
    try:
        connection = get_engine().connect()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"database unavailable: {exc}")
    # The API engine is read-only; seeding needs a writable connection.
    writable = connection.execution_options(postgresql_readonly=False)
    trans = writable.begin()
    try:
        writable.execute(text("SELECT 1 FROM golf.players LIMIT 1"))
    except Exception as exc:  # noqa: BLE001
        trans.rollback()
        connection.close()
        pytest.skip(f"golf schema missing: {exc}")

    writable.execute(
        text(
            "INSERT INTO golf.players (player_id, display_name, is_active, country,"
            " player_bio, primary_tour) VALUES "
            "('T1','Qxqz Testplayer One',true,'Testland',:bio,'PGA Tour'),"
            "('T2','Qxqz Testplayer Two',false,'Otherland',NULL,'PGA Tour'),"
            "('T3','Qxqz Nostats 100%',true,'Testland','not json',NULL)"
        ),
        {"bio": json.dumps({"age": "30"})},
    )
    writable.execute(
        text("INSERT INTO golf.stats_reference VALUES ('ZS1','Zz Test Putting')")
    )
    for pid, season, value, rank in [
        ("T1", SEASON_A, 1.0, 5),
        ("T1", SEASON_B, 2.0, 2),
        ("T2", SEASON_B, 3.0, 1),
    ]:
        writable.execute(
            text(
                "INSERT INTO golf.player_stats (player_id, season, stat_id,"
                " stat_name, stat_value, rank, category, supporting_stat,"
                " supporting_value, player_name, details) VALUES (:p,:s,'ZS1',"
                "'Zz Test Putting',:v,:r,'PUTTING, ZZ_TEST','7','9',"
                "'Zz Testplayer',CAST(:d AS jsonb))"
            ),
            {
                "p": pid,
                "s": season,
                "v": value,
                "r": rank,
                "d": '[{"name":"Avg","value":"1"}]',
            },
        )
    yield writable
    trans.rollback()
    connection.close()


@pytest.fixture()
def client(conn: Connection) -> Iterator[TestClient]:
    app.dependency_overrides[get_conn] = lambda: conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok", "database": "ok"}


def test_players_filters_and_pagination(client: TestClient) -> None:
    r = client.get("/api/v1/players", params={"search": "qxqz testplayer"}).json()
    assert r["total"] == 2
    assert [p["player_id"] for p in r["items"]] == ["T1", "T2"]  # name order

    only_active = client.get(
        "/api/v1/players", params={"search": "qxqz", "active": True}
    ).json()
    assert {p["player_id"] for p in only_active["items"]} == {"T1", "T3"}

    in_season = client.get(
        "/api/v1/players", params={"search": "qxqz", "season": SEASON_A}
    ).json()
    assert [p["player_id"] for p in in_season["items"]] == ["T1"]

    with_stats = client.get(
        "/api/v1/players", params={"search": "qxqz", "has_stats": True}
    ).json()
    assert {p["player_id"] for p in with_stats["items"]} == {"T1", "T2"}

    page = client.get(
        "/api/v1/players", params={"search": "qxqz", "limit": 1, "offset": 1}
    ).json()
    assert page["total"] == 3 and len(page["items"]) == 1


def test_search_escapes_like_wildcards(client: TestClient) -> None:
    hit = client.get("/api/v1/players", params={"search": "100%"}).json()
    assert [p["player_id"] for p in hit["items"]] == ["T3"]
    miss = client.get("/api/v1/players", params={"search": "%%%"}).json()
    assert miss["total"] == 0


def test_player_detail(client: TestClient) -> None:
    d = client.get("/api/v1/players/T1").json()
    assert d["bio"] == {"age": "30"} and d["seasons"] == [SEASON_B, SEASON_A]
    assert client.get("/api/v1/players/T3").json()["bio"] is None  # bad JSON
    assert client.get("/api/v1/players/NOPE").status_code == 404


def test_player_stats_filters(client: TestClient) -> None:
    allrows = client.get("/api/v1/players/T1/stats").json()
    assert [s["season"] for s in allrows] == [SEASON_B, SEASON_A]
    assert allrows[0]["categories"] == ["PUTTING", "ZZ_TEST"]
    assert allrows[0]["details"] == [{"name": "Avg", "value": "1"}]
    assert allrows[0]["stat_value"] == 2.0

    one = client.get("/api/v1/players/T1/stats", params={"season": SEASON_A}).json()
    assert len(one) == 1
    cat = client.get("/api/v1/players/T1/stats", params={"category": "ZZ_TEST"}).json()
    assert len(cat) == 2
    none = client.get("/api/v1/players/T1/stats", params={"category": "ZZ"}).json()
    assert none == []  # exact category match, not substring
    assert client.get("/api/v1/players/NOPE/stats").status_code == 404


def test_history(client: TestClient) -> None:
    h = client.get("/api/v1/players/T1/stats/ZS1/history").json()
    assert [(p["season"], p["rank"]) for p in h["points"]] == [
        (SEASON_A, 5),
        (SEASON_B, 2),
    ]
    assert client.get("/api/v1/players/T1/stats/NOPE/history").status_code == 404


def test_stat_catalogue_and_categories(client: TestClient) -> None:
    stats = client.get("/api/v1/stats", params={"search": "zz test"}).json()
    assert stats == [
        {
            "stat_id": "ZS1",
            "stat_name": "Zz Test Putting",
            "categories": ["PUTTING", "ZZ_TEST"],
        }
    ]
    assert "ZZ_TEST" in client.get("/api/v1/stats/categories").json()


def test_leaders_and_seasons(client: TestClient) -> None:
    lb = client.get("/api/v1/stats/ZS1/leaders").json()  # defaults to latest
    assert lb["season"] == SEASON_B
    assert [r["player_id"] for r in lb["rows"]] == ["T2", "T1"]  # rank order
    lb_a = client.get("/api/v1/stats/ZS1/leaders", params={"season": SEASON_A}).json()
    assert [r["player_id"] for r in lb_a["rows"]] == ["T1"]
    assert client.get("/api/v1/stats/NOPE/leaders").status_code == 404
    assert (
        client.get("/api/v1/stats/ZS1/leaders", params={"limit": 0}).status_code == 422
    )

    seasons = {s["season"]: s for s in client.get("/api/v1/seasons").json()}
    assert seasons[SEASON_B]["players"] == 2 and seasons[SEASON_B]["rows"] == 2


def test_cors_allows_react_dev_origin(client: TestClient) -> None:
    r = client.options(
        "/api/v1/seasons",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_compare_players_side_by_side(client: TestClient) -> None:
    r = client.get(
        "/api/v1/compare",
        params=[("players", "T1"), ("players", "T2"), ("season", SEASON_B)],
    ).json()
    assert r["season"] == SEASON_B
    assert [p["player_id"] for p in r["players"]] == ["T1", "T2"]  # request order
    (stat,) = r["stats"]
    assert stat["stat_id"] == "ZS1" and stat["categories"] == ["PUTTING", "ZZ_TEST"]
    assert [(v["player_id"], v["stat_value"], v["rank"]) for v in stat["values"]] == [
        ("T1", 2.0, 2),
        ("T2", 3.0, 1),
    ]


def test_compare_missing_data_is_null_and_season_defaults(client: TestClient) -> None:
    only_a = client.get(
        "/api/v1/compare",
        params=[("players", "T1"), ("players", "T2"), ("season", SEASON_A)],
    ).json()
    assert [v and v["player_id"] for v in only_a["stats"][0]["values"]] == ["T1", None]
    latest = client.get(
        "/api/v1/compare", params=[("players", "T1"), ("players", "T2")]
    ).json()
    assert latest["season"] == SEASON_B  # latest season with data for these players
    cat = client.get(
        "/api/v1/compare",
        params=[
            ("players", "T1"),
            ("players", "T2"),
            ("season", SEASON_B),
            ("category", "ZZ"),
        ],
    ).json()
    assert cat["stats"] == []  # exact category match


def test_compare_validation(client: TestClient) -> None:
    one = client.get("/api/v1/compare", params=[("players", "T1")])
    assert one.status_code == 422
    five = client.get(
        "/api/v1/compare", params=[("players", f"T{i}") for i in range(5)]
    )
    assert five.status_code == 422
    dupes = client.get("/api/v1/compare", params=[("players", "T1"), ("players", "T1")])
    assert dupes.status_code == 422
    missing = client.get(
        "/api/v1/compare", params=[("players", "T1"), ("players", "NOPE")]
    )
    assert missing.status_code == 404 and "NOPE" in missing.json()["detail"]
    nostats = client.get(
        "/api/v1/compare", params=[("players", "T3"), ("players", "T3x")]
    )
    assert nostats.status_code == 404


def test_compare_history(client: TestClient) -> None:
    h = client.get(
        "/api/v1/compare/history",
        params=[("players", "T1"), ("players", "T2"), ("stat_id", "ZS1")],
    ).json()
    assert h["stat_name"] == "Zz Test Putting"
    by_player = {
        s["player_id"]: [(p["season"], p["rank"]) for p in s["points"]]
        for s in h["series"]
    }
    assert by_player == {"T1": [(SEASON_A, 5), (SEASON_B, 2)], "T2": [(SEASON_B, 1)]}
    nope = client.get(
        "/api/v1/compare/history",
        params=[("players", "T1"), ("players", "T2"), ("stat_id", "NOPE")],
    )
    assert nope.status_code == 404


# --- stats page: percentiles, movers, scatter ---------------------------------


@pytest.fixture()
def stats_conn(conn: Connection) -> Connection:
    """Adds a 5-player field on two seasons for percentile/mover/scatter tests."""
    for i in range(1, 6):
        conn.execute(
            text(
                "INSERT INTO golf.players (player_id, display_name, is_active) "
                "VALUES (:p, :n, true)"
            ),
            {"p": f"M{i}", "n": f"Qxqz Mover {i}"},
        )
    conn.execute(
        text("INSERT INTO golf.stats_reference VALUES ('ZX','Zz X'),('ZY','Zz Y')")
    )
    # ZX ranks: 2026 vs 2025 (M1 rose 5->1, M5 fell 1->5, M3 unchanged, M2/M4 swap)
    ranks_prev = {"M1": 5, "M2": 3, "M3": 2, "M4": 4, "M5": 1}
    ranks_now = {"M1": 1, "M2": 4, "M3": 2, "M4": 3, "M5": 5}
    for season, ranks in ((1997, ranks_prev), (1998, ranks_now)):
        for pid, rank in ranks.items():
            conn.execute(
                text(
                    "INSERT INTO golf.player_stats (player_id, season, stat_id, stat_name,"
                    " stat_value, rank, category, player_name) VALUES "
                    "(:p,:s,'ZX','Zz X',:v,:r,'ZZ_TEST','n'),"
                    "(:p,:s,'ZY','Zz Y',:v2,:r,'ZZ_TEST','n')"
                ),
                {
                    "p": pid,
                    "s": season,
                    "v": 10.0 - rank,
                    "v2": float(rank) * 2,
                    "r": rank,
                },
            )
    return conn


@pytest.fixture()
def stats_client(stats_conn: Connection) -> Iterator[TestClient]:
    app.dependency_overrides[get_conn] = lambda: stats_conn
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_percentile_profile(stats_client: TestClient) -> None:
    r = stats_client.get(
        "/api/v1/players/M1/percentiles", params={"season": 1998}
    ).json()
    assert r["display_name"] == "Qxqz Mover 1"
    zx = next(s for s in r["stats"] if s["stat_id"] == "ZX")
    assert (zx["rank"], zx["field_size"], zx["percentile"]) == (1, 5, 100.0)
    last = stats_client.get(
        "/api/v1/players/M5/percentiles", params={"season": 1998}
    ).json()
    assert next(s for s in last["stats"] if s["stat_id"] == "ZX")["percentile"] == 0.0
    mid = stats_client.get(
        "/api/v1/players/M3/percentiles", params={"season": 1998}
    ).json()
    assert (
        next(s for s in mid["stats"] if s["stat_id"] == "ZX")["percentile"] == 75.0
    )  # rank 2 of 5
    assert (
        stats_client.get("/api/v1/players/M1/percentiles").json()["season"] == 1998
    )  # default
    assert stats_client.get("/api/v1/players/NOPE/percentiles").status_code == 404


def test_percentile_math():
    from app.routers.players import percentile

    assert percentile(1, 1) == 100.0  # a field of one
    assert percentile(1, 200) == 100.0 and percentile(200, 200) == 0.0
    assert percentile(101, 201) == 50.0


def test_movers_use_rank_change(stats_client: TestClient) -> None:
    r = stats_client.get("/api/v1/stats/ZX/movers", params={"limit": 2}).json()
    assert (r["season"], r["compare_to"], r["players_compared"]) == (1998, 1997, 5)
    assert [(m["player_id"], m["rank_change"]) for m in r["improvers"]] == [
        ("M1", 4),
        ("M4", 1),
    ]
    assert [(m["player_id"], m["rank_change"]) for m in r["decliners"]] == [
        ("M5", -4),
        ("M2", -1),
    ]
    assert all(
        m["player_id"] != "M3" for m in r["improvers"] + r["decliners"]
    )  # unchanged
    explicit = stats_client.get(
        "/api/v1/stats/ZX/movers", params={"season": 1998, "compare_to": 1997}
    ).json()
    assert (
        explicit["improvers"][0]["rank_from"] == 5
        and explicit["improvers"][0]["rank_to"] == 1
    )
    assert (
        stats_client.get(
            "/api/v1/stats/ZX/movers", params={"season": 1998, "compare_to": 1998}
        ).status_code
        == 422
    )
    assert (
        stats_client.get("/api/v1/stats/ZX/movers", params={"season": 1997}).status_code
        == 404
    )  # nothing earlier
    assert stats_client.get("/api/v1/stats/NOPE/movers").status_code == 404


def test_scatter(stats_client: TestClient) -> None:
    r = stats_client.get(
        "/api/v1/stats/scatter", params={"x": "ZX", "y": "ZY", "season": 1998}
    ).json()
    assert r["season"] == 1998 and r["x"]["stat_name"] == "Zz X"
    by = {p["player_id"]: p for p in r["points"]}
    assert len(by) == 5 and (by["M1"]["x"], by["M1"]["y"]) == (9.0, 2.0)
    assert (
        stats_client.get("/api/v1/stats/scatter", params={"x": "ZX", "y": "ZY"}).json()[
            "season"
        ]
        == 1998
    )
    assert (
        stats_client.get(
            "/api/v1/stats/scatter", params={"x": "ZX", "y": "ZX"}
        ).status_code
        == 422
    )
    assert (
        stats_client.get(
            "/api/v1/stats/scatter", params={"x": "ZX", "y": "NOPE"}
        ).status_code
        == 404
    )
    assert (
        stats_client.get("/api/v1/stats/scatter", params={"x": "ZX"}).status_code == 422
    )  # y required


def test_pipeline_status_reports_runs_freshness_and_quality(conn: Connection) -> None:
    run_id = conn.execute(
        text(
            "INSERT INTO golf.etl_runs (pipeline, mode, season, status, rows_loaded, finished_at)"
            " VALUES ('stats','backfill',:s,'success',3,now()) RETURNING run_id"
        ),
        {"s": SEASON_B},
    ).scalar_one()
    conn.execute(
        text(
            "INSERT INTO golf.data_quality_results (run_id, season, check_name, status, observed, detail)"
            " VALUES (:r,:s,'zz_check','fail',0.9,'too many nulls'),(:r,:s,'zz_ok','pass',0.0,'fine')"
        ),
        {"r": run_id, "s": SEASON_B},
    )
    app.dependency_overrides[get_conn] = lambda: conn
    try:
        body = TestClient(app).get("/api/v1/pipeline/status", params={"runs": 5}).json()
    finally:
        app.dependency_overrides.clear()
    assert body["overall"] == "fail"
    assert any("zz_check" in reason for reason in body["reasons"])
    fresh = next(s for s in body["seasons"] if s["season"] == SEASON_B)
    assert (
        fresh["rows"] == 2
        and fresh["last_run_status"] == "success"
        and fresh["age_seconds"] < 60
    )
    checks = [q for q in body["quality"] if q["season"] == SEASON_B]
    assert [q["check_name"] for q in checks] == ["zz_check", "zz_ok"]  # worst first
    assert body["runs"][0]["run_id"] == run_id and len(body["runs"]) <= 5


def test_pipeline_stale_threshold_is_configurable(
    conn: Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    conn.execute(
        text(
            "INSERT INTO golf.etl_runs (pipeline, mode, season, status, rows_loaded, finished_at)"
            " VALUES ('stats','backfill',:s,'success',3,now() - interval '40 hours')"
        ),
        {"s": SEASON_B},
    )
    app.dependency_overrides[get_conn] = lambda: conn

    def reasons(hours: float) -> list[str]:
        monkeypatch.setenv("PIPELINE_STALE_AFTER_HOURS", str(hours))
        get_settings.cache_clear()
        try:
            body = TestClient(app).get("/api/v1/pipeline/status").json()
        finally:
            get_settings.cache_clear()
        return [r for r in body["reasons"] if "last loaded" in r]

    try:
        assert not reasons(87600)  # demo setting: never stale
        assert reasons(1)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture()
def tournaments(conn: Connection) -> None:
    conn.execute(
        text(
            "INSERT INTO golf.tournaments (tournament_id, season, name, start_date,"
            " status, category, champion_id, purse_usd) VALUES "
            "('QT1',:s,'Qxqz Open','1999-03-01','completed','SIGNATURE','T2',9000000),"
            "('QT2',:s,'Qxqz Team Event','1999-04-01','completed',NULL,NULL,NULL),"
            "('QT3',:s,'Qxqz Upcoming','1999-05-01','upcoming',NULL,NULL,NULL),"
            "('QT4',:s,'Qxqz Early','1999-02-01','completed',NULL,'T1',1000000)"
        ),
        {"s": SEASON_B},
    )
    conn.execute(
        text(
            "INSERT INTO golf.tournament_results (tournament_id, player_id,"
            " position_text, position, is_tied, status, total_score, to_par,"
            " round_1, round_2, round_3, round_4, fedex_points, earnings_usd) VALUES "
            "('QT1','T2','1',1,false,'finished',270,-18,68,67,68,67,500,1800000),"
            "('QT1','T1','T2',2,true,'finished',272,-16,68,68,68,68,300,900000),"
            "('QT1','T3','CUT',NULL,false,'cut',150,6,75,75,NULL,NULL,0,0),"
            "('QT4','T1','1',1,false,'finished',268,-20,66,67,68,67,500,200000)"
        )
    )


def test_tournament_list_hides_team_events_and_orders_by_date(
    client: TestClient, tournaments: None
) -> None:
    rows = client.get("/api/v1/tournaments", params={"season": SEASON_B}).json()
    assert [t["tournament_id"] for t in rows] == ["QT4", "QT1", "QT3"]  # no QT2
    qt1 = rows[1]
    assert qt1["winner_id"] == "T2" and qt1["winner_name"] == "Qxqz Testplayer Two"
    assert qt1["winning_to_par"] == -18 and qt1["field_size"] == 3
    assert qt1["purse_usd"] == 9_000_000 and qt1["category"] == "SIGNATURE"
    assert rows[2]["winner_id"] is None and rows[2]["field_size"] == 0


def test_tournament_list_filters(client: TestClient, tournaments: None) -> None:
    by_name = client.get(
        "/api/v1/tournaments", params={"season": SEASON_B, "search": "early"}
    ).json()
    assert [t["tournament_id"] for t in by_name] == ["QT4"]
    sig = client.get(
        "/api/v1/tournaments", params={"season": SEASON_B, "category": "signature"}
    ).json()
    assert [t["tournament_id"] for t in sig] == ["QT1"]
    assert client.get("/api/v1/tournaments", params={"season": 1900}).json() == []


def test_tournament_detail_orders_finishers_before_cuts(
    client: TestClient, tournaments: None
) -> None:
    d = client.get("/api/v1/tournaments/QT1").json()
    assert d["name"] == "Qxqz Open" and d["winner_id"] == "T2"
    assert [r["player_id"] for r in d["results"]] == ["T2", "T1", "T3"]
    assert d["results"][0]["rounds"] == [68, 67, 68, 67]
    assert d["results"][1]["is_tied"] is True
    cut = d["results"][2]
    assert cut["status"] == "cut" and cut["rounds"] == [75, 75, None, None]
    assert client.get("/api/v1/tournaments/NOPE").status_code == 404


def test_player_tournament_history_and_totals(
    client: TestClient, tournaments: None
) -> None:
    d = client.get("/api/v1/players/T1/tournaments").json()
    assert [r["tournament_id"] for r in d["results"]] == ["QT1", "QT4"]  # newest first
    assert d["totals"] == {
        "starts": 2,
        "cuts_made": 2,
        "wins": 1,
        "top_10s": 2,
        "earnings_usd": 1_100_000.0,
        "fedex_points": 800.0,
    }
    assert d["results"][0]["field_size"] == 3
    cut = client.get("/api/v1/players/T3/tournaments").json()["totals"]
    assert cut["starts"] == 1 and cut["cuts_made"] == 0
    none = client.get("/api/v1/players/T1/tournaments", params={"season": 1900}).json()
    assert none["totals"]["starts"] == 0 and none["results"] == []
    assert client.get("/api/v1/players/NOPE/tournaments").status_code == 404
