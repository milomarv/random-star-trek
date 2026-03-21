from __future__ import annotations

import asyncio
import re
from datetime import datetime
from typing import Literal
from urllib.parse import quote, quote_plus

import httpx

from app.models import CatalogItem
from app.settings import settings

TVMAZE_SEARCH_URL = "https://api.tvmaze.com/search/shows?q=star%20trek"
TVMAZE_SINGLESEARCH_URL = "https://api.tvmaze.com/singlesearch/shows?q={query}"
TVMAZE_EPISODES_URL = "https://api.tvmaze.com/shows/{show_id}/episodes"
WIKIPEDIA_CATEGORY_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
WIKIPEDIA_FILM_ROOT_CATEGORY = "Category:Star Trek (film franchise)"

CANONICAL_SERIES_QUERIES = [
    "Star Trek: The Original Series",
    "Star Trek: The Animated Series",
    "Star Trek: The Next Generation",
    "Star Trek: Deep Space Nine",
    "Star Trek: Voyager",
    "Star Trek: Enterprise",
    "Star Trek: Discovery",
    "Star Trek: Picard",
    "Star Trek: Lower Decks",
    "Star Trek: Prodigy",
    "Star Trek: Strange New Worlds",
    "Star Trek: Starfleet Academy",
]

EXCLUDED_FILM_TITLES = {
    "star trek: the god thing",
    "star trek: planet of the titans",
}


def _normalize_name(value: str) -> str:
    return value.strip().lower()


def _make_prime_search_link(query: str) -> str:
    domain = settings.normalized_prime_video_domain
    return f"https://{domain}/s?k={quote_plus(query)}&i=instant-video"


def _looks_like_main_star_trek_series(show_name: str) -> bool:
    lowered = _normalize_name(show_name)
    return lowered.startswith("star trek")


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


async def _fetch_show_by_query(client: httpx.AsyncClient, query: str) -> dict | None:
    response = await client.get(TVMAZE_SINGLESEARCH_URL.format(query=quote_plus(query)))
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


async def _fetch_category_members(
    client: httpx.AsyncClient,
    category_title: str,
) -> list[dict]:
    members: list[dict] = []
    continue_token: str | None = None

    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category_title,
            "cmlimit": "max",
            "format": "json",
        }
        if continue_token is not None:
            params["cmcontinue"] = continue_token

        response = await client.get(WIKIPEDIA_CATEGORY_URL, params=params)
        response.raise_for_status()
        payload = response.json()
        members.extend(payload.get("query", {}).get("categorymembers", []))

        continue_token = payload.get("continue", {}).get("cmcontinue")
        if continue_token is None:
            break

    return members


async def fetch_star_trek_episodes(
    client: httpx.AsyncClient,
) -> list[CatalogItem]:
    canonical_tasks = [
        _fetch_show_by_query(client, query) for query in CANONICAL_SERIES_QUERIES
    ]
    canonical_results = await asyncio.gather(*canonical_tasks)

    search_response = await client.get(TVMAZE_SEARCH_URL)
    search_response.raise_for_status()
    search_results = search_response.json()

    collected: list[dict] = [show for show in canonical_results if show is not None]
    collected.extend(result.get("show", {}) for result in search_results)

    shows: list[dict] = []
    seen_show_ids: set[int] = set()
    for show in collected:
        name = show.get("name")
        show_id = show.get("id")
        show_type = (show.get("type") or "").lower()
        if not name or not show_id or not _looks_like_main_star_trek_series(name):
            continue
        if show_type and show_type not in {"scripted", "animation"}:
            continue

        if show_id in seen_show_ids:
            continue

        seen_show_ids.add(show_id)
        shows.append(show)

    tasks = [
        client.get(TVMAZE_EPISODES_URL.format(show_id=show["id"])) for show in shows
    ]
    episode_responses = await asyncio.gather(*tasks)

    items: list[CatalogItem] = []
    for show, episodes_response in zip(shows, episode_responses, strict=True):
        episodes_response.raise_for_status()
        episodes = episodes_response.json()
        series_name = show.get("name", "Star Trek")

        for episode in episodes:
            season = episode.get("season")
            episode_number = episode.get("number")
            episode_title = episode.get("name") or "Untitled Episode"
            premiered = episode.get("airdate")
            year = None
            if premiered:
                try:
                    year = datetime.fromisoformat(premiered).year
                except ValueError:
                    year = None

            prime_search = series_name
            image = episode.get("image") or {}

            items.append(
                CatalogItem(
                    kind="episode",
                    title=episode_title,
                    series=series_name,
                    season=season,
                    episode_number=episode_number,
                    year=year,
                    banner_url=image.get("original") or image.get("medium"),
                    prime_video_url=_make_prime_search_link(prime_search),
                )
            )

    return items


async def fetch_star_trek_films(client: httpx.AsyncClient) -> list[CatalogItem]:
    root_members = await _fetch_category_members(client, WIKIPEDIA_FILM_ROOT_CATEGORY)
    root_titles = [
        entry.get("title")
        for entry in root_members
        if entry.get("title")
        and entry.get("ns") == 0
        and not entry.get("title", "").startswith("List of")
    ]

    film_subcategories = [
        entry.get("title")
        for entry in root_members
        if entry.get("title")
        and entry.get("ns") == 14
        and "films based on star trek" in _normalize_name(entry.get("title", ""))
    ]
    subcategory_titles_only = [
        title for title in film_subcategories if isinstance(title, str)
    ]

    subcategory_results = await asyncio.gather(
        *[_fetch_category_members(client, title) for title in subcategory_titles_only]
    )
    subcategory_titles = [
        entry.get("title")
        for members in subcategory_results
        for entry in members
        if entry.get("title")
        and entry.get("ns") == 0
        and not entry.get("title", "").startswith("List of")
    ]

    titles = [title for title in [*root_titles, *subcategory_titles] if title]
    summary_tasks = [
        client.get(WIKIPEDIA_SUMMARY_URL.format(title=quote(title, safe="")))
        for title in titles
    ]
    summary_responses = await asyncio.gather(*summary_tasks)

    seen_titles: set[str] = set()
    items: list[CatalogItem] = []

    for summary_response in summary_responses:
        if summary_response.status_code != 200:
            continue

        movie = summary_response.json()
        title = movie.get("title")
        if not title:
            continue
        normalized_title = _normalize_name(title)
        if not normalized_title.startswith("star trek"):
            continue
        if normalized_title in EXCLUDED_FILM_TITLES:
            continue
        if normalized_title.startswith("development of"):
            continue
        if " debate" in normalized_title:
            continue
        if normalized_title in seen_titles:
            continue

        description = (movie.get("description") or "").lower()
        if "film" not in description:
            continue
        if any(
            keyword in description for keyword in {"unproduced", "fan film", "proposed"}
        ):
            continue

        seen_titles.add(normalized_title)

        year_match = re.search(r"(19|20)\d{2}", description)
        year = None
        if year_match:
            year = int(year_match.group(0))

        original_image = movie.get("originalimage") or {}
        thumbnail = movie.get("thumbnail") or {}
        banner = original_image.get("source") or thumbnail.get("source")

        items.append(
            CatalogItem(
                kind="film",
                title=title,
                series="Star Trek Films",
                year=year,
                film_era=_classify_film_era(year),
                banner_url=banner,
                prime_video_url=_make_prime_search_link(title),
            )
        )

    return items
