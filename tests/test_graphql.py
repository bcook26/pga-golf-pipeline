import pandas as pd
import pytest
from extract.cache import PayloadCache
from extract.pgatour_graphql import GraphQLError, PGATourGraphQLSource, stat_categories
from transform.stats_graphql import transform_stat_details


def _player(pid, name, rank, cols):
    return {
        "__typename": "StatDetailsPlayer",
        "playerId": pid,
        "playerName": name,
        "country": "USA",
        "rank": rank,
        "stats": [
            {"statName": n, "statValue": v, "supportingData": None} for n, v in cols
        ],
    }


ITEM = {
    "stat_id": "02675",
    "categories": ["STROKES_GAINED", "SCORING"],
    "payload": {
        "statId": "02675",
        "statTitle": "SG: Total",
        "rows": [
            _player(
                "1",
                "A",
                1,
                [("Avg", "2.496"), ("Total SG:T", "154.741"), ("Rounds", "62")],
            ),
            _player("2", "B", 2, [("Avg", "-"), ("Total SG:T", "1,000")]),
            {
                "__typename": "StatDetailTourAvg",
                "displayName": "Tour Avg",
                "value": "0.0",
            },
        ],
    },
}


def test_transform_maps_columns_and_details():
    stats, players = transform_stat_details([ITEM], 2024)
    a = stats[stats.player_id == "1"].iloc[0]
    assert a.stat_value == pytest.approx(2.496)
    assert a.supporting_stat == "154.741" and a.supporting_value == "62"
    assert a.category == "STROKES_GAINED, SCORING" and a["rank"] == 1
    assert a.field_average == 0.0
    assert a.details == [
        {"name": "Avg", "value": "2.496"},
        {"name": "Total SG:T", "value": "154.741"},
        {"name": "Rounds", "value": "62"},
    ]
    b = stats[stats.player_id == "2"].iloc[0]
    assert pd.isna(b.stat_value)  # "-" -> NULL
    assert pd.isna(b.supporting_value)
    assert sorted(players.player_id) == ["1", "2"]  # tour-avg row ignored


def test_transform_empty():
    stats, players = transform_stat_details([], 2024)
    assert stats.empty and players.empty


def test_stat_categories_dedupes_and_orders():
    sd = {
        "statCategories": [
            {
                "category": "A",
                "subCategories": [{"stats": [{"statId": "1", "statTitle": "t"}]}],
            },
            {
                "category": "B",
                "subCategories": [{"stats": [{"statId": "1", "statTitle": "t"}]}],
            },
        ]
    }
    assert stat_categories(sd) == {"1": {"title": "t", "categories": ["A", "B"]}}


class FakeClient:
    def __init__(self, responses):
        self.responses, self.calls = responses, []

    def post_json(self, url, payload, headers=None):
        v = payload["variables"]
        self.calls.append((v["statId"], v["year"]))
        return self.responses(v)


def _sd(stat_id, year):
    return {
        "data": {
            "statDetails": {
                "statId": stat_id,
                "year": year,
                "statTitle": f"S{stat_id}",
                "statHeaders": [],
                "yearPills": [{"year": 2026}, {"year": 2024}],
                "statCategories": [
                    {
                        "category": "C",
                        "subCategories": [
                            {
                                "stats": [
                                    {"statId": "02675", "statTitle": "S02675"},
                                    {"statId": "9", "statTitle": "S9"},
                                ]
                            }
                        ],
                    }
                ],
                "rows": [_player("1", "A", 1, [("Avg", "1")])],
            }
        }
    }


def test_graphql_source_seasons_and_caching():
    class R:
        def __init__(self):
            self.d = {}

        def get(self, k):
            return self.d.get(k)

        def setex(self, k, t, v):
            self.d[k] = v

    client = FakeClient(lambda v: _sd(v["statId"], v["year"] or 2026))
    src = PGATourGraphQLSource(client, PayloadCache(R()), "key")  # type: ignore[arg-type]
    assert src.current_season() == 2026
    assert src.supports_season(2024) and not src.supports_season(2022)

    items = src.fetch_season_stat_details(2024, max_workers=1)
    assert {i["stat_id"] for i in items} == {"02675", "9"}
    n = len(client.calls)
    src2 = PGATourGraphQLSource(client, src.cache, "key")  # type: ignore[arg-type]
    src2.fetch_season_stat_details(2024, max_workers=1)
    assert len(client.calls) == n  # second pass fully cached


def test_graphql_errors_raise_and_missing_key_rejected():
    client = FakeClient(lambda v: {"errors": [{"message": "boom"}]})
    src = PGATourGraphQLSource(client, PayloadCache(None), "key")  # type: ignore[arg-type]
    with pytest.raises(GraphQLError):
        src.current_season()
    with pytest.raises(ValueError):
        PGATourGraphQLSource(client, PayloadCache(None), "")  # type: ignore[arg-type]
