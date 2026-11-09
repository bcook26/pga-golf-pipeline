"""PGA Tour GraphQL source: season stat leaderboards, including history.

One ``StatDetails`` call returns every player for one stat in one season, so a
season costs ~one request per stat instead of one per player, and past seasons
are available (the page-data source only serves the current one).

The API is undocumented and authenticated with the key the public website
ships to browsers; keep request rates low (see settings) and review the site's
terms of use before any non-personal use.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from extract.cache import PayloadCache
from extract.http import PoliteClient
from settings import get_settings
from tqdm import tqdm

log = logging.getLogger(__name__)

TOUR_CODE = "R"
DISCOVERY_STAT_ID = "02675"  # any stat works; its response lists all stat ids
SEASON_META_TTL = 24 * 3600
PAST_SEASON_TTL = 30 * 24 * 3600  # completed seasons effectively never change

STAT_DETAILS_QUERY = """
query StatDetails($tourCode: TourCode!, $statId: String!, $year: Int,
                  $eventQuery: StatDetailEventQuery) {
  statDetails(tourCode: $tourCode, statId: $statId, year: $year,
              eventQuery: $eventQuery) {
    __typename tourCode year displaySeason statId statType
    yearPills { year displaySeason }
    statTitle statHeaders
    statCategories {
      category displayName
      subCategories { displayName stats { statId statTitle } }
    }
    rows {
      ... on StatDetailsPlayer {
        __typename playerId playerName country rank
        stats { statName statValue supportingData }
      }
      ... on StatDetailTourAvg { __typename displayName value }
    }
  }
}
"""


SCHEDULE_QUERY = """
query Schedule($year: String) {
  schedule(tourCode: "R", year: $year) {
    seasonYear
    completed { tournaments { ...T } }
    upcoming { tournaments { ...T } }
  }
}
fragment T on ScheduleTournament {
  id tournamentName startDate courseName city stateCode countryCode
  championId purse tournamentStatus sequenceNumber
  tournamentCategoryInfo { type }
}
"""

TOURNAMENT_RESULTS_QUERY = """
query Results($id: ID!) {
  tournamentPastResults(id: $id) {
    id rounds additionalDataHeaders
    players {
      position total parRelativeScore additionalData
      player { id displayName country }
      rounds { score parRelativeScore }
    }
  }
}
"""

COMPLETED = "COMPLETED"
# A finished event's results are final bar official-money tweaks; refresh daily.
COMPLETED_CURRENT_TTL = 24 * 3600


class GraphQLError(RuntimeError):
    pass


def stat_categories(stat_details: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """{stat_id: {"title": str, "categories": [str, ...]}} from statCategories."""
    out: dict[str, dict[str, Any]] = {}
    for cat in stat_details.get("statCategories") or []:
        for sub in cat.get("subCategories") or []:
            for stat in sub.get("stats") or []:
                entry = out.setdefault(
                    stat["statId"], {"title": stat["statTitle"], "categories": []}
                )
                if cat["category"] not in entry["categories"]:
                    entry["categories"].append(cat["category"])
    return out


class PGATourGraphQLSource:
    name = "pgatour-graphql"

    def __init__(
        self,
        client: PoliteClient,
        cache: PayloadCache,
        api_key: str,
        url: str = "https://orchestrator.pgatour.com/graphql",
        current_season_ttl: int = 3600,
    ) -> None:
        if not api_key:
            raise ValueError("PGA_GRAPHQL_KEY is not set")
        self._client = client
        self._cache = cache
        self._url = url
        self._current_ttl = current_season_ttl
        self._headers = {
            "content-type": "application/json",
            "origin": "https://www.pgatour.com",
            "x-api-key": api_key,
            "x-pgat-platform": "web",
        }
        self._meta: dict[int | None, dict[str, Any]] = {}
        self._current: int | None = None

    @classmethod
    def from_settings(cls, cache: PayloadCache | None = None) -> "PGATourGraphQLSource":
        s = get_settings()
        client = PoliteClient(
            requests_per_second=s.requests_per_second,
            max_retries=s.max_retries,
            timeout=s.request_timeout,
            user_agent=s.user_agent,
        )
        cache = cache or PayloadCache.from_url(s.redis_url, s.cache_ttl_seconds)
        return cls(
            client,
            cache,
            s.graphql_api_key,
            s.graphql_url,
            current_season_ttl=s.current_season_ttl_seconds,
        )

    @property
    def cache(self) -> PayloadCache:
        return self._cache

    # -- transport ------------------------------------------------------

    def _stat_details(self, stat_id: str, season: int | None) -> dict[str, Any]:
        body = self._client.post_json(
            self._url,
            {
                "operationName": "StatDetails",
                "query": STAT_DETAILS_QUERY,
                "variables": {
                    "tourCode": TOUR_CODE,
                    "statId": stat_id,
                    "year": season,
                    "eventQuery": None,
                },
            },
            headers=self._headers,
        )
        if body.get("errors"):
            raise GraphQLError(str(body["errors"])[:500])
        return body["data"]["statDetails"]

    def _post(self, operation: str, query: str, variables: dict[str, Any]) -> Any:
        body = self._client.post_json(
            self._url,
            {"operationName": operation, "query": query, "variables": variables},
            headers=self._headers,
        )
        if body.get("errors"):
            raise GraphQLError(str(body["errors"])[:500])
        return body["data"]

    # -- season discovery -----------------------------------------------

    def _season_meta(self, season: int | None) -> dict[str, Any]:
        """Available years and the stat catalogue for ``season``."""
        if season not in self._meta:

            def produce() -> dict[str, Any]:
                sd = self._stat_details(DISCOVERY_STAT_ID, season)
                return {
                    "years": [int(y["year"]) for y in sd["yearPills"]],
                    "stats": stat_categories(sd),
                    "season": int(sd["year"]),
                }

            key = f"gql:meta:{season}"
            self._meta[season] = self._cache.get_or_set(key, produce, SEASON_META_TTL)
        return self._meta[season]

    def current_season(self) -> int:
        if self._current is None:
            self._current = int(self._season_meta(None)["season"])
        return self._current

    def supports_season(self, season: int) -> bool:
        return season in self._season_meta(None)["years"]

    # -- extraction -----------------------------------------------------

    def _stat_payload(self, stat_id: str, season: int) -> dict[str, Any]:
        """Slimmed, cacheable StatDetails payload for one stat + season."""

        def produce() -> dict[str, Any]:
            sd = self._stat_details(stat_id, season)
            return {
                "statId": sd["statId"],
                "statTitle": sd["statTitle"],
                "statHeaders": sd["statHeaders"],
                "rows": [r for r in sd["rows"] if r],
            }

        ttl = self._current_ttl if season == self.current_season() else PAST_SEASON_TTL
        return self._cache.get_or_set(f"gql:stat:{season}:{stat_id}", produce, ttl)

    def fetch_season_stat_details(
        self, season: int, max_workers: int = 4
    ) -> list[dict[str, Any]]:
        """Every stat's leaderboard for ``season``.

        Returns [{"stat_id", "categories": [...], "payload": {...}}]. A stat
        that fails after retries is logged and skipped so one bad stat does
        not sink the season.
        """
        catalogue = self._season_meta(season)["stats"]

        def fetch(stat_id: str) -> dict[str, Any] | None:
            try:
                payload = self._stat_payload(stat_id, season)
            except Exception as exc:  # noqa: BLE001
                log.warning("Stat %s (%s) failed: %s", stat_id, season, exc)
                return None
            return {
                "stat_id": stat_id,
                "categories": catalogue[stat_id]["categories"],
                "payload": payload,
            }

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            results = list(
                tqdm(
                    pool.map(fetch, catalogue),
                    total=len(catalogue),
                    desc=f"Extracting {season} stats",
                )
            )
        return [r for r in results if r is not None]

    # -- tournaments ----------------------------------------------------

    def _schedule(self, season: int) -> list[dict[str, Any]]:
        """Every scheduled tournament for ``season`` (completed + upcoming)."""

        def produce() -> list[dict[str, Any]]:
            data = self._post("Schedule", SCHEDULE_QUERY, {"year": str(season)})
            sched = data["schedule"]
            months = (sched.get("completed") or []) + (sched.get("upcoming") or [])
            return [t for m in months for t in m["tournaments"]]

        ttl = self._current_ttl if season == self.current_season() else PAST_SEASON_TTL
        return self._cache.get_or_set(f"gql:schedule:{season}", produce, ttl)

    def _tournament_results(self, tournament_id: str, season: int) -> dict[str, Any]:
        def produce() -> dict[str, Any]:
            # No ``year`` argument: the id (e.g. R2023002) already names the
            # edition. ``year`` is not a calendar year (the API's own season
            # pills look like 20260) and an unrecognised value silently falls
            # back to the latest edition, which once loaded the wrong results.
            data = self._post(
                "Results", TOURNAMENT_RESULTS_QUERY, {"id": tournament_id}
            )
            results = data["tournamentPastResults"]
            if results.get("id") != tournament_id:
                raise GraphQLError(
                    f"asked for results of {tournament_id}, got {results.get('id')}"
                )
            return results

        ttl = (
            COMPLETED_CURRENT_TTL
            if season == self.current_season()
            else PAST_SEASON_TTL
        )
        return self._cache.get_or_set(f"gql:results:v2:{tournament_id}", produce, ttl)

    def fetch_season_tournaments(
        self, season: int, max_workers: int = 4
    ) -> list[dict[str, Any]]:
        """Schedule plus results for ``season``.

        Returns [{"tournament": {...}, "results": {...} | None}]. Results are
        fetched only for completed tournaments; one that fails after retries is
        logged and kept without results so the schedule stays complete.
        """
        schedule = self._schedule(season)

        def fetch(t: dict[str, Any]) -> dict[str, Any]:
            if t.get("tournamentStatus") != COMPLETED:
                return {"tournament": t, "results": None}
            try:
                return {
                    "tournament": t,
                    "results": self._tournament_results(t["id"], season),
                }
            except Exception as exc:  # noqa: BLE001
                log.warning("Results for %s failed: %s", t["id"], exc)
                return {"tournament": t, "results": None}

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            return list(
                tqdm(
                    pool.map(fetch, schedule),
                    total=len(schedule),
                    desc=f"Extracting {season} tournaments",
                )
            )
