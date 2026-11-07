# Random Star Trek Picker

FastAPI app that returns a random pick from all available Star Trek episodes and films.

- Episodes are pulled from TVMaze.
- Films are pulled from TMDB collections and search.
- Prime Video links are generated as direct Prime search URLs.

The frontend uses HTMX + server-side templates, so it stays lightweight.

## Features

- Random choice across one combined pool of episodes and films.
- Type filters via checkboxes (episodes and films).
- Series filters via exclusion checkboxes (including Prodigy).
- Film-era exclusion filter to remove batches of films.
- Browser-persisted filter selections (your choices are restored on revisit).
- Auto-refreshable catalog from external APIs, with in-memory caching.
- Docker Compose support.

## Configuration

Edit `.env` and adjust values:

- `APP_TITLE`: FastAPI application title shown in API docs.
- `APP_BASE_PATH`: URL path prefix when served behind a reverse proxy (for example `/random-star-trek`). Leave empty for root.
- `PRIME_VIDEO_DOMAIN`: Amazon domain used to build Prime links (for example `www.amazon.de`).
- `REQUEST_TIMEOUT_SECONDS`: HTTP timeout for upstream APIs.
- `CACHE_TTL_SECONDS`: cache time before pulling fresh upstream data.
- `USER_AGENT`: User-Agent header sent to upstream APIs.
- `PERSIST_FILTERS`: Enables server-side filter persistence (`true` or `false`).
- `TMDB_API_TOKEN`: TMDB API Read Access Token; required to load films.
- `TMDB_LANGUAGE`: language for TMDB movie titles and metadata (defaults to `en-US`).

If `PERSIST_FILTERS=true`, filter state is written to `data/filters_state.json`.

Use `.env.example` as the template for creating your local `.env`.

## Run Locally (uv)

```bash
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload
```

Open http://localhost:8000

If `APP_BASE_PATH` is set (for example `/random-star-trek`), open:

http://localhost:8000/random-star-trek

## Run With Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Open http://localhost:8000

If using Traefik with `APP_BASE_PATH=/random-star-trek`, open:

https://homenet.tale-alioth.ts.net/random-star-trek

## API Endpoints

- `GET {APP_BASE_PATH}/`: web UI
- `GET {APP_BASE_PATH}/api/random`: JSON payload for one random item
	- Optional query params:
		- `include_kinds=episode|film` (repeatable query parameter)
		- `exclude_series=<exact series name>` (repeatable query parameter)
		- `exclude_film_eras=tos|tng|kelvin|other` (repeatable)
- `GET {APP_BASE_PATH}/api/pool-stats`: selected vs available totals for episodes/films
- `GET {APP_BASE_PATH}/api/search`: search in the filtered catalog
	- Query params:
		- `q=<search text>`
		- `include_kinds=episode|film` (repeatable)
		- `exclude_series=<exact series name>` (repeatable)
		- `exclude_film_eras=tos|tng|kelvin|other` (repeatable)
- `GET {APP_BASE_PATH}/api/release-timeline`: year buckets for the filtered catalog
- `GET {APP_BASE_PATH}/api/filters`: read persisted filter state (only when `PERSIST_FILTERS=true`)
- `POST {APP_BASE_PATH}/api/filters`: save persisted filter state (only when `PERSIST_FILTERS=true`)
- `GET {APP_BASE_PATH}/partials/random-card`: HTML fragment used by HTMX

## Notes

- Episode catalog data is fetched from TVMaze and film data from TMDB, then cached in memory for `CACHE_TTL_SECONDS`.
- This product uses the TMDB API but is not endorsed or certified by TMDB.
- Prime links are generated as search URLs; for some fan-series episodes, a YouTube search link is used as fallback.
- Docker Compose mounts `./data` into `/app/data` so persisted filter state survives container restarts.
