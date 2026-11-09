#!/usr/bin/env bash
# Copy the local warehouse (the `golf` schema) into a hosted Postgres such as
# Neon. Needs the local docker compose postgres service running, plus Docker
# for the pg_restore client (no local Postgres tools required).
#
#   TARGET_DATABASE_URL='postgresql://user:pass@host/db?sslmode=require' \
#     ./scripts/deploy_db.sh
#
# Use the DIRECT (non-pooled) connection string and the database owner role.
# The URL is passed through the environment, never printed or put in argv.
# DOCKER_RUN_ARGS adds options to the docker run calls (e.g. --network host
# when testing against a database on this machine).
set -euo pipefail
cd "$(dirname "$0")/.."

: "${TARGET_DATABASE_URL:?set TARGET_DATABASE_URL to the hosted database connection string}"

env_value() { # KEY=value from .env, tolerating spaces around "=" and quotes
  grep -E "^$1[[:space:]]*=" .env 2>/dev/null | head -1 \
    | sed -E "s/^[^=]*=[[:space:]]*//; s/^[\"']//; s/[\"'][[:space:]]*$//" || true
}
SRC_USER="$(env_value ETL_DB_USER)"; SRC_USER="${SRC_USER:-postgres}"
SRC_DB="$(env_value ETL_DB_NAME)";   SRC_DB="${SRC_DB:-ADHOC_GOLF}"

dump="$(mktemp)"
trap 'rm -f "$dump"' EXIT

echo "Dumping local ${SRC_DB} (schema golf)..."
docker compose exec -T postgres \
  pg_dump -U "$SRC_USER" -d "$SRC_DB" --schema=golf -Fc --no-owner --no-privileges > "$dump"
echo "Dump size: $(du -h "$dump" | cut -f1)"

echo "Restoring into the hosted database..."
docker run --rm -i -e TARGET_DATABASE_URL ${DOCKER_RUN_ARGS:-} postgres:16 \
  sh -c 'pg_restore --no-owner --no-privileges --clean --if-exists -d "$TARGET_DATABASE_URL"' < "$dump"

echo "Row counts on the hosted database:"
docker run --rm -e TARGET_DATABASE_URL ${DOCKER_RUN_ARGS:-} postgres:16 sh -c \
  'psql "$TARGET_DATABASE_URL" -At -c "SELECT '"'"'player_stats'"'"', count(*) FROM golf.player_stats UNION ALL SELECT '"'"'tournament_results'"'"', count(*) FROM golf.tournament_results UNION ALL SELECT '"'"'players'"'"', count(*) FROM golf.players"'
echo "Done."
