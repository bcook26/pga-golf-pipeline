import pandas as pd
import pytest
from extract.cache import PayloadCache
from extract.pgatour_graphql import PGATourGraphQLSource
from quality.tournaments import champion_mismatches
from transform.tournaments import (
    parse_int,
    parse_money,
    parse_position,
    transform_results,
    transform_tournaments,
)


def _tournament(tid="R2025016", status="COMPLETED", **over):
    t = {
        "id": tid,
        "tournamentName": "The Sentry",
        "startDate": 1735776000000,  # 2025-01-02 UTC
        "courseName": "Plantation Course at Kapalua",
        "city": "Kapalua, Maui",
        "stateCode": "HI",
        "countryCode": "USA",
        "championId": "32839",
        "purse": "$20,000,000",
        "tournamentStatus": status,
        "sequenceNumber": 10,
        "tournamentCategoryInfo": {"type": "SIGNATURE"},
    }
    t.update(over)
    return t


def _row(pid, name, position, total, to_par, rounds, extra):
    return {
        "position": position,
        "total": total,
        "parRelativeScore": to_par,
        "additionalData": extra,
        "player": {"id": pid, "displayName": name, "country": "United States"},
        "rounds": [{"score": r, "parRelativeScore": "0"} for r in rounds],
    }


RESULTS = {
    "additionalDataHeaders": ["FedExCup Pts", "Official Money"],
    "players": [
        _row(
            "1",
            "Winner",
            "1",
            "257",
            "-35",
            ["65", "65", "62", "65"],
            ["700.000", "$3,600,000.00"],
        ),
        _row(
            "2",
            "Tied",
            "T2",
            "260",
            "-32",
            ["66", "65", "64", "65"],
            ["400.000", "$2,160,000.00"],
        ),
        _row("3", "Missed", "CUT", "145", "+1", ["73", "72"], ["0.000", "$0.00"]),
        _row("4", "Hurt", "W/D", "--", "--", ["80"], ["--", "--"]),
    ],
}


def test_parsers():
    assert parse_int("257") == 257
    assert parse_int("-35") == -35
    assert parse_int("+3") == 3
    assert parse_int("E") == 0
    assert parse_int("--") is None and parse_int(None) is None
    assert parse_money("$3,600,000.00") == 3_600_000.0
    assert parse_money("700.000") == 700.0
    assert parse_money("--") is None
    assert parse_position("1") == (1, False, "finished")
    assert parse_position("T11") == (11, True, "finished")
    assert parse_position("CUT") == (None, False, "cut")
    assert parse_position("W/D") == (None, False, "wd")
    assert parse_position("DQ") == (None, False, "dq")
    assert parse_position("???") == (None, False, "other")


def test_transform_tournaments():
    items = [
        {"tournament": _tournament(), "results": None},
        {
            "tournament": _tournament(
                "R2025099", "UPCOMING", tournamentCategoryInfo=None, purse=None
            ),
            "results": None,
        },
    ]
    df = transform_tournaments(items, 2025)
    first = df.iloc[0]
    assert first["start_date"].isoformat() == "2025-01-02"
    assert first["purse_usd"] == 20_000_000
    assert first["status"] == "completed" and first["category"] == "SIGNATURE"
    assert pd.isna(df.iloc[1]["purse_usd"]) and pd.isna(df.iloc[1]["category"])
    assert df["season"].eq(2025).all()


def test_transform_results_handles_cuts_and_withdrawals():
    results, players = transform_results(
        [{"tournament": _tournament(), "results": RESULTS}]
    )
    by_player = results.set_index("player_id")
    win = by_player.loc["1"]
    assert (win["position"], win["status"], win["total_score"], win["to_par"]) == (
        1,
        "finished",
        257,
        -35,
    )
    assert win["fedex_points"] == 700 and win["earnings_usd"] == 3_600_000
    assert bool(by_player.loc["2", "is_tied"]) is True
    cut = by_player.loc["3"]
    assert cut["status"] == "cut" and pd.isna(cut["position"])
    assert cut["round_1"] == 73 and pd.isna(cut["round_3"])
    wd = by_player.loc["4"]
    assert wd["status"] == "wd" and pd.isna(wd["total_score"])
    assert set(players["player_id"]) == {"1", "2", "3", "4"}
    assert players.set_index("player_id").loc["1", "display_name"] == "Winner"


def test_results_are_matched_by_header_not_position():
    swapped = {
        "additionalDataHeaders": ["Official Money", "FedExCup Pts"],
        "players": [
            _row("1", "A", "1", "270", "-10", ["68"] * 4, ["$1,000.00", "50.0"])
        ],
    }
    results, _ = transform_results([{"tournament": _tournament(), "results": swapped}])
    assert results.iloc[0]["fedex_points"] == 50
    assert results.iloc[0]["earnings_usd"] == 1000


def test_tournaments_without_results_contribute_no_rows():
    results, players = transform_results(
        [{"tournament": _tournament(status="UPCOMING"), "results": None}]
    )
    assert results.empty and players.empty


def test_duplicate_players_in_a_tournament_are_collapsed():
    dup = {**RESULTS, "players": RESULTS["players"] + [RESULTS["players"][0]]}
    results, _ = transform_results([{"tournament": _tournament(), "results": dup}])
    assert len(results) == 4


class FakeClient:
    def __init__(self, fail_for=(), wrong_edition=()):
        self.wrong_edition = set(wrong_edition)
        self.calls = []
        self.fail_for = set(fail_for)

    def post_json(self, url, body, headers=None):
        self.calls.append(body["operationName"])
        op, variables = body["operationName"], body["variables"]
        if op == "StatDetails":
            return {
                "data": {
                    "statDetails": {
                        "year": 2025,
                        "yearPills": [{"year": "2025"}],
                        "statCategories": [],
                    }
                }
            }
        if op == "Schedule":
            done = [_tournament("R1"), _tournament("R2"), _tournament("R3")]
            return {
                "data": {
                    "schedule": {
                        "seasonYear": "2025",
                        "completed": [{"tournaments": done}],
                        "upcoming": [{"tournaments": [_tournament("R4", "UPCOMING")]}],
                    }
                }
            }
        if op == "Results":
            if variables["id"] in self.fail_for:
                return {"errors": [{"message": "boom"}]}
            if variables["id"] in self.wrong_edition:
                return {
                    "data": {"tournamentPastResults": {**RESULTS, "id": "R9999999"}}
                }
            assert "year" not in variables
            return {
                "data": {"tournamentPastResults": {**RESULTS, "id": variables["id"]}}
            }
        raise AssertionError(op)


def _source(client):
    return PGATourGraphQLSource(client, PayloadCache(None, 60), "key")


def test_fetch_requests_results_only_for_completed_tournaments():
    client = FakeClient()
    items = _source(client).fetch_season_tournaments(2025, max_workers=1)
    assert [i["tournament"]["id"] for i in items] == ["R1", "R2", "R3", "R4"]
    assert client.calls.count("Results") == 3
    assert items[3]["results"] is None


def test_one_failing_tournament_does_not_sink_the_season():
    items = _source(FakeClient(fail_for={"R2"})).fetch_season_tournaments(
        2025, max_workers=1
    )
    assert [bool(i["results"]) for i in items] == [True, False, True, False]


@pytest.mark.parametrize("bad", [None, {}])
def test_missing_additional_data_is_tolerated(bad):
    payload = {
        "additionalDataHeaders": [],
        "players": [
            {**_row("1", "A", "1", "270", "-10", ["68"] * 4, []), "additionalData": bad}
        ],
    }
    results, _ = transform_results([{"tournament": _tournament(), "results": payload}])
    assert pd.isna(results.iloc[0]["fedex_points"])


def test_results_for_a_different_edition_are_rejected():
    """The API falls back to the latest edition for an unrecognised year; a
    mismatched id must never be loaded under the requested tournament."""
    items = _source(FakeClient(wrong_edition={"R2"})).fetch_season_tournaments(
        2025, max_workers=1
    )
    assert [bool(i["results"]) for i in items] == [True, False, True, False]


def test_champion_check_flags_results_from_another_edition():
    items = [{"tournament": _tournament("R1"), "results": RESULTS}]
    tournaments = transform_tournaments(items, 2025)
    results, _ = transform_results(items)
    # champion in the schedule is 32839, but the position-1 row is player "1"
    assert champion_mismatches(tournaments, results) == ["R1"]
    tournaments["champion_id"] = "1"
    assert champion_mismatches(tournaments, results) == []


def test_champion_check_ignores_unfinished_or_resultless_tournaments():
    items = [
        {"tournament": _tournament("R1", "UPCOMING"), "results": None},
        {"tournament": _tournament("R2"), "results": None},
    ]
    results, _ = transform_results(items)
    assert champion_mismatches(transform_tournaments(items, 2025), results) == []
