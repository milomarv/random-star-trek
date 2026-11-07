from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Literal
from urllib.parse import quote_plus

import httpx

from .catalog_config import (
    CANONICAL_SERIES_QUERIES,
    FAN_SERIES_QUERIES,
    SERIES_NAME_OVERRIDES,
    TMDB_API_BASE,
    TMDB_EXTRA_FILM_QUERIES,
    TMDB_FILM_COLLECTION_IDS,
    TMDB_IMAGE_BASE,
    TVMAZE_EPISODES_URL,
    TVMAZE_SINGLESEARCH_URL,
    YOUTUBE_FALLBACK_SERIES,
)
from app.models import CatalogItem
from app.settings import settings

logger = logging.getLogger(__name__)

UPSTREAM_CONCURRENCY = 4
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 0.5


def _normalize_name(value: str) -> str:
    return value.strip().lower()


def _make_prime_search_link(query: str) -> str:
    domain = settings.normalized_prime_video_domain
    return f"https://{domain}/s?k={quote_plus(query)}&i=instant-video"


def _make_youtube_search_link(query: str) -> str:
    return f"https://www.youtube.com/results?search_query={quote_plus(query)}"


def _make_streaming_link(
    *,
    series_name: str,
    title: str,
    kind: Literal["episode", "film"],
) -> str:
    normalized_series = _normalize_name(series_name)
    if kind == "episode" and normalized_series in YOUTUBE_FALLBACK_SERIES:
        return _make_youtube_search_link(f"{series_name} {title}")

    if kind == "film":
        return _make_prime_search_link(title)
    return _make_prime_search_link(series_name)


def _canonicalize_series_name(series_name: str) -> str:
    normalized_series_name = _normalize_name(series_name)
    return SERIES_NAME_OVERRIDES.get(normalized_series_name, series_name)


def _classify_film_era(
    year: int | None,
) -> Literal["tos", "tng", "kelvin", "other"] | None:
    if year is None:
        return None
    if year <= 1991:
        return "tos"
    if 1992 <= year <= 2002:
        return "tng"
    if 2009 <= year <= 2016:
        return "kelvin"
    return "other"


async def _get_with_retry(
    client: httpx.AsyncClient,
    limiter: asyncio.Semaphore,
    url: str,
    **kwargs,
) -> httpx.Response:
    for attempt in range(RETRY_ATTEMPTS - 1):
        try:
            async with limiter:
                response = await client.get(url, **kwargs)
        except httpx.TransportError as exc:
            logger.warning("Transient error for %s (attempt %d): %s", url, attempt + 1, exc)
        else:
            if response.status_code != 429 and response.status_code < 500:
                return response
            logger.warning(
                "Upstream returned %d for %s (attempt %d)",
                response.status_code,
                url,
                attempt + 1,
            )
        await asyncio.sleep(RETRY_BACKOFF_SECONDS * 2**attempt)

    async with limiter:
        return await client.get(url, **kwargs)


async def _fetch_show_by_query(
    client: httpx.AsyncClient, limiter: asyncio.Semaphore, query: str
) -> dict | None:
    response = await _get_with_retry(
        client,
        limiter,
        TVMAZE_SINGLESEARCH_URL.format(query=quote_plus(query)),
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


async def fetch_star_trek_episodes(
    client: httpx.AsyncClient,
) -> list[CatalogItem]:
    limiter = asyncio.Semaphore(UPSTREAM_CONCURRENCY)
    canonical_tasks = [
        _fetch_show_by_query(client, limiter, query)
        for query in CANONICAL_SERIES_QUERIES
    ]
    fan_tasks = [
        _fetch_show_by_query(client, limiter, query) for query in FAN_SERIES_QUERIES
    ]
    canonical_results, fan_results = await asyncio.gather(
        asyncio.gather(*canonical_tasks), asyncio.gather(*fan_tasks)
    )

    shows: list[dict] = []
    canon_by_show_id: dict[int, bool] = {}
    seen_show_ids: set[int] = set()
    for show, is_canon in [
        *((show, True) for show in canonical_results if show is not None),
        *((show, False) for show in fan_results if show is not None),
    ]:
        show_id = show.get("id")
        if not show.get("name") or not show_id or show_id in seen_show_ids:
            continue
        seen_show_ids.add(show_id)
        canon_by_show_id[show_id] = is_canon
        shows.append(show)

    tasks = [
        _get_with_retry(client, limiter, TVMAZE_EPISODES_URL.format(show_id=show["id"]))
        for show in shows
    ]
    episode_responses = await asyncio.gather(*tasks)

    items: list[CatalogItem] = []
    for show, episodes_response in zip(shows, episode_responses, strict=True):
        episodes_response.raise_for_status()
        episodes = episodes_response.json()
        series_name = _canonicalize_series_name(show.get("name", "Star Trek"))
        is_canon = canon_by_show_id[show["id"]]

        for episode in episodes:
            season = episode.get("season")
            episode_number = episode.get("number")
            episode_title = episode.get("name") or "Untitled Episode"
            premiered = episode.get("airdate")
            year = None
            air_date = None
            if premiered:
                try:
                    air_date = datetime.fromisoformat(premiered).date()
                    year = air_date.year
                except ValueError:
                    pass

            image = episode.get("image") or {}

            items.append(
                CatalogItem(
                    kind="episode",
                    title=episode_title,
                    series=series_name,
                    season=season,
                    episode_number=episode_number,
                    year=year,
                    air_date=air_date,
                    canon=is_canon,
                    banner_url=image.get("original") or image.get("medium"),
                    prime_video_url=_make_streaming_link(
                        series_name=series_name,
                        title=episode_title,
                        kind="episode",
                    ),
                )
            )

    return items


async def fetch_star_trek_films(client: httpx.AsyncClient) -> list[CatalogItem]:
    if not settings.tmdb_api_token.strip():
        logger.warning("TMDB_API_TOKEN is missing; skipping film catalog fetch")
        return []

    headers = {"Authorization": f"Bearer {settings.tmdb_api_token.strip()}"}
    params = {"language": settings.tmdb_language}
    limiter = asyncio.Semaphore(UPSTREAM_CONCURRENCY)

    async def fetch_collection(collection_id: int) -> list[dict]:
        response = await _get_with_retry(
            client,
            limiter,
            f"{TMDB_API_BASE}/collection/{collection_id}",
            headers=headers,
            params=params,
        )
        response.raise_for_status()
        return response.json().get("parts", [])

    async def fetch_extra(query: str) -> dict | None:
        response = await _get_with_retry(
            client,
            limiter,
            f"{TMDB_API_BASE}/search/movie",
            headers=headers,
            params={**params, "query": query, "include_adult": "false"},
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        normalized_query = _normalize_name(query)
        return next(
            (
                movie
                for movie in results
                if _normalize_name(movie.get("title", "")) == normalized_query
            ),
            None,
        )

    collection_results, extra_results = await asyncio.gather(
        asyncio.gather(
            *(fetch_collection(collection_id) for collection_id in TMDB_FILM_COLLECTION_IDS)
        ),
        asyncio.gather(*(fetch_extra(query) for query in TMDB_EXTRA_FILM_QUERIES)),
    )
    movies = [movie for collection in collection_results for movie in collection]
    movies.extend(movie for movie in extra_results if movie is not None)

    seen_ids: set[int] = set()
    items: list[CatalogItem] = []
    for movie in movies:
        movie_id = movie.get("id")
        title = movie.get("title")
        if not movie_id or not title or movie_id in seen_ids:
            continue
        seen_ids.add(movie_id)

        release_date = movie.get("release_date")
        air_date = None
        year = None
        if release_date:
            try:
                air_date = date.fromisoformat(release_date)
                year = air_date.year
            except ValueError:
                pass

        image_path = movie.get("backdrop_path") or movie.get("poster_path")
        banner = f"{TMDB_IMAGE_BASE}{image_path}" if image_path else None
        items.append(
            CatalogItem(
                kind="film",
                title=title,
                series="Star Trek Films",
                year=year,
                air_date=air_date,
                film_era=_classify_film_era(year),
                banner_url=banner,
                prime_video_url=_make_streaming_link(
                    series_name="Star Trek Films",
                    title=title,
                    kind="film",
                ),
            )
        )

    return items
