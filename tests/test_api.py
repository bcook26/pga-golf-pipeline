"""API tests against a real Postgres (compose DB locally, service in CI).

Each test seeds fixture rows inside a transaction that is rolled back, so the
tests never read or modify real warehouse data. Skipped if no DB is reachable.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
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
