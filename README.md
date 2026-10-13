# Mini Enterprise Collaboration & Workflow Application

This repository contains the primary FastAPI and React application in
`backend/` and `frontend/`. The separate Phase 4 microservice experiment is
under `phase4/` and `phase4frontend/`; its Compose file is not the deployment
configuration for this primary application.

## Stack

- FastAPI, SQLAlchemy, Alembic, PostgreSQL
- React, Vite, Axios, React Router
- Redis is optional for dashboard caching and is required for shared
  production rate limiting

## Local setup

### Backend

From PowerShell:

```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create `backend/.env` locally (it is ignored by Git). Set at least:

```dotenv
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:5432/DATABASE
SECRET_KEY=replace-with-a-long-random-secret
APP_ENV=development
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

Use a local PostgreSQL database, or configure a different SQLAlchemy URL
supported by the installed driver. Do not put real credentials in source
control, issues, logs, or this README.

Start the API from `backend/`:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Interactive API documentation is available at `http://localhost:8000/docs`.

### Frontend

From another terminal:

```powershell
cd frontend
npm ci
```

The default API URL is `http://localhost:8000`. To override it, set
`VITE_API_BASE_URL` in the frontend build/development environment. Start Vite:

```powershell
npm run dev
```

The development frontend runs at `http://localhost:5173`. Keep the API and UI
on `localhost` (rather than mixing `localhost` and `127.0.0.1`) so development
cookies behave consistently.

## Configuration

Settings are loaded from the process environment and `backend/.env`.

| Variable | Purpose | Development default / production guidance |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy database connection | Required. Use the intended environment's PostgreSQL URL for migrations and service startup. |
| `SECRET_KEY` | JWT signing and CSRF token signing | Required. Use a unique, high-entropy value; do not reuse the example placeholder. |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access-token lifetime | `60` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh-token and cookie lifetime | `7` |
| `REFRESH_COOKIE_SECURE` | Adds the Secure cookie attribute | `false` locally; **must be `true` in production** (HTTPS). |
| `REFRESH_COOKIE_SAMESITE` | Refresh/CSRF cookie SameSite policy | `lax`; use `none` only for a truly cross-site HTTPS deployment, together with Secure cookies. |
| `CORS_ALLOWED_ORIGINS` | Explicit credentialed browser origins | Local Vite origins by default. Set only trusted production origins; wildcards are rejected. |
| `APP_ENV` | Environment behavior | `development`; use `production` for production validation. |
| `RATE_LIMIT_REDIS_URL` | Shared auth rate-limit store | Optional locally (process-local limiter); required in production. |
| `LOGIN_RATE_LIMIT_REQUESTS` / `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | Login rate limit | `5` / `60` |
| `FORGOT_PASSWORD_RATE_LIMIT_REQUESTS` / `FORGOT_PASSWORD_RATE_LIMIT_WINDOW_SECONDS` | Forgot-password rate limit | `5` / `3600` |
| `RESET_PASSWORD_RATE_LIMIT_REQUESTS` / `RESET_PASSWORD_RATE_LIMIT_WINDOW_SECONDS` | Reset-password rate limit | `5` / `900` |
| `REDIS_URL` | Optional dashboard-summary cache | Unset disables caching; Redis failures fall back to live database queries. |
| `DASHBOARD_CACHE_TTL_SECONDS` | Dashboard cache lifetime | `60` |
| `PASSWORD_RESET_TOKEN_EXPIRE_MINUTES` | Password-reset token lifetime | `30` |
| `PASSWORD_RESET_DELIVERY_MODE` | Reset-link delivery mode | `disabled`; `smtp` or development-only `development_file` are also supported. |
| `PASSWORD_RESET_FRONTEND_URL` | Base URL used to construct reset links | Required for SMTP delivery; use the deployed frontend origin. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_STARTTLS` | SMTP provider configuration | Defaults to port `587` and STARTTLS enabled. Configure credentials as a matched username/password pair. |
| `VITE_API_BASE_URL` | Frontend API origin | `http://localhost:8000` |

For an app and API on different sites, browsers may block third-party cookies
even with `SameSite=None; Secure`. Prefer serving them from the same site or
through a same-site reverse proxy. Add the frontend origin to
`CORS_ALLOWED_ORIGINS`; CORS is not a substitute for HTTPS or CSRF validation.

Refresh tokens are issued only as HttpOnly cookies and are not returned in API
JSON. The frontend keeps access and CSRF tokens in memory, and clears legacy
token entries from localStorage at startup. Refresh and logout require the
CSRF header obtained through the `/auth/csrf` bootstrap endpoint.

## Tests and checks

Run from `backend/` with its virtual environment active:

```powershell
python -B -m unittest discover -s tests -v
python -m compileall -q app alembic tests
```

Run from `frontend/`:

```powershell
npm run lint
npm run build
```

The backend tests use isolated SQLite databases and mocked Redis/SMTP
dependencies where appropriate. They do not require applying migrations to
the configured development database. A real Redis instance, SMTP provider,
and production browser/proxy setup require separate integration validation.

## Database migrations

Alembic reads `DATABASE_URL` from the backend settings. Before deploying a
migration, back up the target database, confirm the deployment environment's
connection configuration, and inspect its current and target revisions from
`backend/`:

```powershell
python -m alembic current
python -m alembic heads
```

The pending list-query index migration is
`b07d61a5e2cf_add_list_query_indexes.py` (revision `b07d61a5e2cf`, parent
`26474fe525d5`). The acceptance audit observed current revision
`26474fe525d5` and head `b07d61a5e2cf`. Apply it only in the intended
environment, after review and backup, with:

```powershell
python -m alembic upgrade head
```

Do not run that command against development or production until the target
database has been explicitly selected and approved. The migration creates
eight named indexes and its downgrade drops those same indexes; the model
metadata declares corresponding index names. The audit did not apply or
downgrade the migration.

## Phase 5 implementation status and known gaps

- Login, refresh rotation/replay rejection, logout revocation, and reset-token
  expiry/single use are covered by backend tests. A local browser smoke test
  verified login, session restoration after reload, logout, and protected-route
  redirection; production HTTPS, reverse-proxy, and cross-site cookie behavior
  have not been verified.
- Auth rate limits return HTTP 429 in tests. Redis rate limiting uses a mocked
  Redis client in tests; live Redis behavior has not been tested.
- Dashboard cache key isolation, TTL, invalidation, and Redis-unavailable
  fallback are tested with fakes. A live Redis service has not been tested.
- The task, user, document, approval/history, notification, and audit-log list
  APIs have bounded SQL pagination and supported filters/sorting. Task
  activities have bounded pagination but fixed ordering and no list filters.
- The Kanban endpoint and task-comments endpoint still return unbounded
  collections; large boards/comment histories can therefore cause
  unnecessary database and response work.
- The eight list-query indexes are pending application in the intended
  deployment database.
- Forgot/reset-password pages are implemented. SMTP delivery is configurable
  but has not been tested against a live provider; delivery remains disabled
  unless explicitly configured.
- No Compose deployment for the primary FastAPI application is provided.

## Separate Phase 4 experiment

The Auth0/microservice experiment and its Docker Compose configuration remain
under `phase4/` and `phase4frontend/`. They use separate services and
configuration and should not be used to deploy the primary FastAPI
application described above.
