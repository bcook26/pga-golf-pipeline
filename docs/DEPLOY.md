# Deploying for free (Netlify + Neon + Render)

```
Browser ──> Netlify (React build)
   │
   └──────> Render free web service (FastAPI, rate limited) ──> Neon free Postgres
                                                                    ▲
GitHub Actions (daily ETL) ─────────────────────────────────────────┘
```

| Piece | Service | Free-tier behaviour |
| --- | --- | --- |
| Frontend | Netlify | static hosting, free `*.netlify.app` URL |
| API | Render web service | sleeps after ~15 min idle; first request takes up to ~1 min |
| Database | Neon Postgres | 0.5 GB (the warehouse is ~180 MB); compute suspends when idle |
| Daily ETL | GitHub Actions | scheduled workflow, uses the repo's free minutes |

Free-tier limits change; check each service's current pricing page before
relying on a number here.

## 1. Create the accounts (all free)

- Neon: https://console.neon.tech/signup
- Render: https://dashboard.render.com/register (sign in with GitHub)
- Netlify: https://app.netlify.com/signup (sign in with GitHub)

## 2. Database (Neon)

1. Create a project (for example `golf-stats`), Postgres 16 or newer. Pick a
   region close to the Render region you will use (for example US East).
2. Open **Connect** and copy the **direct** connection string (turn *Connection
   pooling* off). It looks like `postgresql://owner:***@ep-xxx.region.aws.neon.tech/neondb?sslmode=require`.
3. Copy the local warehouse into it (needs the local compose database running
   and Docker; the URL is read from the environment and never printed):

   ```sh
   TARGET_DATABASE_URL='postgresql://...neon.tech/neondb?sslmode=require' ./scripts/deploy_db.sh
   ```

   It prints row counts at the end; they should match your local database.
4. Recommended: give the API a read-only login. In the Neon **SQL Editor**:

   ```sql
   CREATE ROLE api_readonly LOGIN PASSWORD 'choose-a-long-random-password';
   GRANT USAGE ON SCHEMA golf TO api_readonly;
   GRANT SELECT ON ALL TABLES IN SCHEMA golf TO api_readonly;
   ALTER DEFAULT PRIVILEGES IN SCHEMA golf GRANT SELECT ON TABLES TO api_readonly;
   ```

   The API URL is then the same string with `api_readonly` and that password.
   (The API already opens read-only transactions; this makes the database
   enforce it too.) Keep the owner URL for the ETL only.

## 3. API (Render)

1. **New + > Blueprint**, pick this repository and branch. Render reads
   `render.yaml` and creates `golf-stats-api` on the free plan.
2. When asked, set `DATABASE_URL` to the **read-only** Neon URL and
   `CORS_ORIGINS` to your Netlify URL (step 4; use a placeholder now and
   update it afterwards).
3. After the first deploy, note the URL (`https://golf-stats-api.onrender.com`
   or similar) and check it: `curl https://<api>/live` then `curl https://<api>/health`.

The health check uses `/live`, which never touches the database, so Render's
polling cannot keep Neon awake and use up its free compute hours.

## 4. Frontend (Netlify)

1. **Add new site > Import an existing project**, pick this repository and
   branch. `netlify.toml` supplies the build settings.
2. Before the first build, add the environment variable
   `VITE_API_URL` = the Render URL (no trailing slash). It is baked into the
   bundle at build time, so changing it needs a redeploy.
3. **Site configuration > Change site name** to something short and
   descriptive, for example `golf-stats-lab` (becomes
   `https://golf-stats-lab.netlify.app`; names are first come, first served).
   Avoid "PGA" in the name.
4. Put that URL in Render's `CORS_ORIGINS` (comma-separate several) and let
   the API redeploy.

## 5. Daily ETL (GitHub Actions)

Add repository secrets (**Settings > Secrets and variables > Actions**):

- `DATABASE_URL`: the Neon **owner** URL (the ETL writes)
- `PGA_GRAPHQL_KEY`: the same key as in your local `.env`

`.github/workflows/etl.yml` then runs an incremental load daily and can be
started by hand from the **Actions** tab. **Scheduled and manually dispatched
workflows only exist on the repository's default branch**, so the workflow
must be merged there before it appears.

## Rate limiting

The API refuses excess traffic with `429 Too Many Requests` and a
`Retry-After` header; the UI shows the wait time. Three sliding windows:

| Limit | Default | Env var |
| --- | --- | --- |
| per client, per minute | 60 | `RATE_LIMIT_PER_MINUTE` |
| per client, per hour | 600 | `RATE_LIMIT_PER_HOUR` |
| whole service, per hour | 3000 | `RATE_LIMIT_GLOBAL_PER_HOUR` |

The global limit is the guarantee: however many clients there are, and even if
client identification is spoofed, the service cannot serve more than that per
hour, which bounds database compute. Only allowed requests are counted, so
being refused never extends a block. `/live`, `/health` and CORS preflights
are exempt. Visitors never cause calls to the PGA Tour: the public API reads
only the warehouse, and the ETL has its own 2 requests/second limiter. `0`
disables an individual limit (local docker compose does this by default).

### Check the rate limiter

`RATE_LIMIT_PROXY_HOPS` is the number of proxies that append to
`X-Forwarded-For` in front of the API. If it is too low, every visitor shares
one bucket (strict, but unfair); too high, per-client limits can be
bypassed (the global limit still holds). After deploying:

```sh
for i in $(seq 70); do curl -s -o /dev/null -w "%{http_code}\n" https://<api>/api/v1/seasons; done | sort | uniq -c
```

Expect about 60 `200` then `429`. Then look at the Render logs: the
`rate limit (client) hit by <address>` line should show **your** public IP.
If it shows a Render/Cloudflare address, raise `RATE_LIMIT_PROXY_HOPS` by one.

## Trade-offs and limits

- First visit after idle is slow (Render wake-up, then Neon resume); the UI
  explains this after a few seconds.
- The site republishes PGA Tour data from an undocumented API: it carries an
  unofficial/not-affiliated notice, keeps the key server-side, and the public
  API never calls the PGA Tour. Review their terms before sharing widely.
- Airflow is not deployed (nowhere free to run it); GitHub Actions replaces it
  for the hosted copy, and the compose profile still demonstrates it locally.
