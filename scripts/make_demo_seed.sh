#!/usr/bin/env bash
# Snapshot the dev stack's golf data into demo/golf_demo.dump (data only; the
# schema comes from db/01_schema.sql when the demo database is created).
set -euo pipefail
cd "$(dirname "$0")/.."
user=${ETL_DB_USER:-postgres}; db=${ETL_DB_NAME:-ADHOC_GOLF}
docker compose exec -T postgres pg_dump -U "$user" -d "$db" \
  --schema=golf -Fc --data-only --no-owner > demo/golf_demo.dump
ls -lh demo/golf_demo.dump
