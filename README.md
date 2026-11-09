# Golf ETL Project (In Progress)

A data-engineering project that ingests PGA Tour player and season statistics
into a PostgreSQL warehouse, with incremental loads, season backfills, payload
caching and an Airflow schedule. A FastAPI backend and React frontend will sit
on top of the warehouse (not built yet).

## Architecture

```mermaid
flowchart LR
    SRC["GolfDataSource<br/>(swappable extractor)"] -->|rate-limited + retried HTTP| CACHE[(Redis payload cache)]
    CACHE --> EX[extract]
    EX --> TR[transform<br/>coerce types, dedupe keys]
    TR --> LD[load<br/>idempotent upserts]
    LD --> PG[(PostgreSQL<br/>golf schema)]
    AF[Airflow DAGs] -->|full_pipeline.py| EX
    LD --> AUDIT[golf.etl_runs audit log]
```

| Layer | Path | Notes |
| --- | --- | --- |
| Extract | `etl/extract/` | source protocols (`base.py`); `pgatour_graphql.py` (stats + history) and `pgatour_pages.py` (player directory); `http.py` rate limiter + retries; `cache.py` Redis cache |
| Transform | `etl/transform/` | Normalises players/stats, coerces types, enforces the primary key |
| Load | `etl/load/`, `etl/database/` | Chunked, transactional `INSERT ... ON CONFLICT DO UPDATE` |
| Orchestration | `etl/pipeline/`, `etl/full_pipeline.py` | `runner.py` plans seasons and records every run |
| Scheduling | `airflow/dags/` | Daily incremental DAG + manual backfill DAG |
| API | `backend/app/` | FastAPI read API over the warehouse for the React frontend |
| Schema | `db/01_schema.sql` | Idempotent DDL, applied automatically by docker compose |

### Design decisions

- **Swappable extractor.** The pipeline depends only on the `GolfDataSource`
  protocol. Moving to another provider means writing one class.
- **Polite scraping.** Global token-spacing rate limiter (`REQUESTS_PER_SECOND`),
  exponential-backoff retries on 429/5xx honouring `Retry-After`, an
  identifying User-Agent, and `robots.txt` respected (player and stats pages
  are not disallowed).
- **Redis payload cache.** Parsed payloads are cached (including "no stats"
  results), so re-runs and backfills don't re-hit the source. If Redis is down
  the pipeline logs a warning and runs uncached.
- **Idempotent loads.** Upserts keyed on `(player_id, season, stat_id)`; all
  chunks of a load run in one transaction; duplicate keys are rejected up front.
- **Auditability.** `golf.etl_runs` records each run's mode, season, status,
  row count and any skip reason.

## Getting started

```sh
cp .env.example .env              # set DB_PASSWORD
docker compose up -d              # Postgres (host port 5433) + Redis
# in .env: ETL_DB_PORT=5433, ETL_DB_NAME=ADHOC_GOLF

uv sync --dev
cd etl
uv run python full_pipeline.py --mode incremental
```

Without Docker, point `ETL_DB_*` (host, port, name, user) at any Postgres and apply `db/01_schema.sql`.

### Modes

```sh
python full_pipeline.py --mode incremental                       # players + current season
python full_pipeline.py --mode backfill                          # last 4 seasons
python full_pipeline.py --mode backfill --seasons 2024 2025 --force
python full_pipeline.py --mode incremental --stats-source pages  # current season via page data
```

Completed past seasons are skipped on re-run unless `--force` is passed. The
current season is always refreshed.

### Running the ETL with Airflow

Airflow runs the same `full_pipeline.py` CLI shown above, scheduled and
tracked. Everything runs in Docker; no local Airflow install is needed.

**1. Prerequisites**

- Docker with Compose v2.
- `.env` containing at least `DB_PASSWORD` and `PGA_GRAPHQL_KEY`
  (see `.env.example`). Compose passes these into the containers.

**2. Start the stack**

```sh
docker compose --profile airflow up -d --build   # Postgres, Redis, API, Airflow
docker compose ps                                # wait until postgres/redis are healthy
```

The first start builds the image (~2 min) and initialises Airflow's metadata
database (`airflow` DB in the same Postgres). The warehouse schema in
`ADHOC_GOLF` is created automatically on the first start of an empty volume.

**3. Log in**

Open http://localhost:8080 and sign in as `admin`. The generated password is
in the container:

```sh
docker compose exec airflow cat /opt/airflow/standalone_admin_password.txt
```

**4. The two DAGs** (both are paused on first start - flip the toggle to enable)

| DAG | Schedule | What it runs |
| --- | --- | --- |
| `golf_etl_incremental` | daily 08:00 UTC | `full_pipeline.py --mode incremental` - refresh players + current season |
| `golf_etl_backfill` | manual only | `full_pipeline.py --mode backfill` - last 4 seasons, or the ones you choose |

**5. Run a DAG now**

From the UI: open the DAG -> **Trigger DAG** (play button). For
`golf_etl_backfill` choose **Trigger DAG w/ config** and set the params:

```json
{"seasons": [2024, 2025], "force": true}
```

- `seasons`: list of seasons; empty list = last 4 seasons.
- `force`: `true` reloads seasons that are already loaded (otherwise skipped).

Or from the CLI:

```sh
docker compose exec airflow airflow dags unpause golf_etl_incremental
docker compose exec airflow airflow dags trigger golf_etl_incremental
docker compose exec airflow airflow dags trigger golf_etl_backfill \
    --conf '{"seasons": [2025], "force": false}'
docker compose exec airflow airflow dags list-runs -d golf_etl_incremental
```

**6. Check the result**

- Airflow UI -> DAG -> Grid -> task -> **Logs**. The last line summarises the
  run: `Done in ... | loaded={2026: 81551} skipped={} | cache hits=... misses=...`.
- The warehouse audit log records every run, including skips and failures:

```sh
docker compose exec postgres psql -U postgres -d ADHOC_GOLF -c \
  "select run_id, pipeline, mode, season, status, rows_loaded, detail, started_at
   from golf.etl_runs order by run_id desc limit 10"
```

**7. Stop**

```sh
docker compose --profile airflow down        # keep data (volumes)
docker compose --profile airflow down -v     # also delete the database and Airflow state
```

**Notes**

- A cold backfill makes ~400 rate-limited requests per season (~4 minutes
  each); repeat runs are served from the Redis cache.
- The ETL runs in its own virtualenv inside the image because Airflow 2.x pins
  SQLAlchemy < 2. `airflow standalone` is a dev-only all-in-one runner; a real
  deployment would use separate scheduler/webserver services and a proper
  executor.
- Unpausing a DAG makes Airflow create a run for the most recent missed
  schedule interval, so expect one immediate run for `golf_etl_incremental`.
- Retries, alerting and schedules are still defaults to be tuned. If a run
  fails, `golf.etl_runs.detail` holds the error and the task retries twice,
  10 minutes apart.

### Keeping the current season fresh

Current-season payloads are cached for `CURRENT_SEASON_TTL_SECONDS` (default
1 hour; completed seasons for 30 days). Each load of a season replaces the
GraphQL-sourced rows for the stats that were fetched in one transaction, so
rows that disappear upstream (e.g. a player dropping off a leaderboard) are
removed rather than lingering. Rows from other sources, and stats that failed
to fetch, are left untouched.

### Quality checks

```sh
uv run pytest -q && uv run mypy etl backend && uv run black --check . && uv run isort --check-only .
```

GitHub Actions run formatting (black/isort), flake8, and mypy + pytest on every push.

## API (FastAPI)

Read-only JSON API over the warehouse for the React/TypeScript frontend.

```sh
docker compose up -d --build api                  # http://localhost:8000
# or locally, from backend/:
cd backend && uv run uvicorn app.main:app --reload
```

Interactive docs and the OpenAPI schema (usable to generate TypeScript
types): http://localhost:8000/docs and `/openapi.json`.

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | liveness + database check |
| `GET /api/v1/seasons` | seasons loaded, with player/stat/row counts |
| `GET /api/v1/players` | search/filter players (`search`, `country`, `active`, `has_stats`, `season`, `limit`, `offset`) |
| `GET /api/v1/players/{id}` | player profile, parsed bio, seasons with stats |
| `GET /api/v1/players/{id}/stats` | a player's stats (`season`, `stat_id`, `category`) |
| `GET /api/v1/players/{id}/stats/{stat_id}/history` | one stat across seasons (trend charts) |
| `GET /api/v1/stats` | stat catalogue (`search`, `category`) |
| `GET /api/v1/stats/categories` | category names for filter dropdowns |
| `GET /api/v1/stats/{stat_id}/leaders` | leaderboard (`season` defaults to latest, `limit`) |

Design notes: the API connects with a read-only transaction (the database
rejects writes), uses parameterised SQL only (LIKE wildcards in search are
escaped), validates and caps paging parameters, and allows CORS from
`CORS_ORIGINS` (default: the Vite and CRA dev servers). Tests seed their own
rows in a rolled-back transaction, so they never touch real data.

## Data sources

| Source | Class | Serves | Used for |
| --- | --- | --- | --- |
| Page data (`__NEXT_DATA__`) | `PGATourPageSource` | current season | player directory; `--stats-source pages` |
| PGA Tour GraphQL `StatDetails` | `PGATourGraphQLSource` | current + history (2004+) | season stats (default) |

The GraphQL source fetches one whole-season leaderboard per stat (~400 stats
per season, all players at once) instead of one request per player. Rows map
into `golf.player_stats` as `stat_value` (first column), `supporting_stat`
(second), `supporting_value` (last), and every column the API returned is kept
in the `details` JSONB column. Players that appear in historical leaderboards
but not in the current directory are stubbed so the foreign key holds.

Set `PGA_GRAPHQL_KEY` in `.env` (see `.env.example`). It is the key the public
website ships to browsers; never commit it.

## Known limitations

- Both sources read **undocumented** pgatour.com interfaces that can change
  without notice. Request rates are deliberately low and cached (completed
  seasons are cached for 30 days). Review pgatour.com's terms of use before
  any non-personal use. The GraphQL host publishes no robots.txt.
- Leaderboards only include players ranked in each stat, so a player's
  `player_stats` rows exist only for seasons where they qualified.
- `above_or_below` is not provided by the GraphQL source (NULL for those rows).

## Roadmap

- [x] FastAPI service over the warehouse
- [ ] React + TypeScript frontend (next)
- [ ] Course statistics
- [ ] Dependabot, integration tests against a Postgres service container
