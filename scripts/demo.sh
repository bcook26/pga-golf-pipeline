#!/usr/bin/env bash
# One-command demo: needs only Docker (Compose v2). No PGA key, no Airflow.
#   scripts/demo.sh        start (or resume) the demo and print the URLs
#   scripts/demo.sh down   stop it and delete its data
set -euo pipefail
cd "$(dirname "$0")/.."

dc() { docker compose -p golf-demo --env-file demo/demo.env "$@"; }
env_val() { grep -E "^$1=" demo/demo.env | cut -d= -f2-; }
WEB=$(env_val WEB_HOST_PORT); API=$(env_val API_HOST_PORT)

if [ "${1:-}" = "down" ]; then
  dc down -v --remove-orphans
  echo "Demo stopped and its data removed."
  exit 0
fi

command -v docker >/dev/null || { echo "Docker is required: https://docs.docker.com/get-docker/" >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo "Docker Compose v2 is required." >&2; exit 1; }
[ -f demo/golf_demo.dump ] || { echo "demo/golf_demo.dump is missing (see README)." >&2; exit 1; }

echo "Building and starting the demo (first run takes a few minutes)..."
dc up -d --build --wait postgres redis api web

rows=$(dc exec -T postgres psql -U postgres -d ADHOC_GOLF -tAc "SELECT count(*) FROM golf.player_stats")
if [ "$rows" = "0" ]; then
  echo "Loading the data snapshot..."
  dc exec -T postgres pg_restore -U postgres -d ADHOC_GOLF --data-only --no-owner --exit-on-error < demo/golf_demo.dump
fi

printf "Waiting for the API"
for _ in $(seq 1 60); do
  curl -fsS "http://localhost:$API/health" >/dev/null 2>&1 && break
  printf "."; sleep 1
done
echo

cat <<EOM

Demo is running (snapshot data; no live PGA Tour calls):
  App       http://localhost:$WEB
  API docs  http://localhost:$API/docs
Stop and clean up:  scripts/demo.sh down
EOM
