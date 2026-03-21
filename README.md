# Random Star Trek Picker

FastAPI app that returns a random pick from all available Star Trek episodes and films.

- Episodes are pulled from TVMaze.
- Films are pulled from Wikipedia APIs (category + page summaries).
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

- `APP_BASE_PATH`: URL path prefix when served behind a reverse proxy (for example `/random-star-trek`).
- `PRIME_VIDEO_DOMAIN`: Amazon domain used to build Prime links (for example `www.amazon.de`).
- `CACHE_TTL_SECONDS`: cache time before pulling fresh upstream data.
- `REQUEST_TIMEOUT_SECONDS`: HTTP timeout for upstream APIs.

## Run Locally (uv)

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Open http://localhost:8000

If `APP_BASE_PATH` is set (for example `/random-star-trek`), open:

http://localhost:8000/random-star-trek

## Run With Docker Compose

```bash
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
- `GET {APP_BASE_PATH}/partials/random-card`: HTML fragment used by HTMX

