from __future__ import annotations

import logging
import random
import time
from collections import Counter
from datetime import date

import httpx

from app.clients import fetch_star_trek_episodes, fetch_star_trek_films
from app.models import CatalogItem
from app.settings import settings

logger = logging.getLogger(__name__)

REFRESH_RETRY_SECONDS = 60


class CatalogService:
    def __init__(self) -> None:
        self._cache: list[CatalogItem] = []
        self._cache_expires_at: float = 0.0

    async def get_catalog(self, *, force_refresh: bool = False) -> list[CatalogItem]:
        now = time.time()
        if not force_refresh and self._cache and now < self._cache_expires_at:
            return self._cache

        previous_films = [item for item in self._cache if item.kind == "film"]
        timeout = httpx.Timeout(settings.request_timeout_seconds)
        headers = {"User-Agent": settings.user_agent}
        async with httpx.AsyncClient(
            timeout=timeout, headers=headers, follow_redirects=True
        ) as client:
            try:
                episodes: list[CatalogItem] | None = await fetch_star_trek_episodes(
                    client
                )
            except Exception:
                logger.exception("Failed to fetch Star Trek episodes")
                episodes = None
            try:
                films = await fetch_star_trek_films(client)
            except Exception:
                logger.exception("Failed to fetch Star Trek films")
                films = previous_films

        if episodes is None:
            return self._serve_stale_cache(now)

        combined = [*episodes, *films]
        if not combined:
            return self._serve_stale_cache(now)

        self._cache = combined
        self._cache_expires_at = now + settings.cache_ttl_seconds
        return self._cache

    def _serve_stale_cache(self, now: float) -> list[CatalogItem]:
        if not self._cache:
            raise RuntimeError(
                "No Star Trek episodes or films were returned from upstream APIs."
            )
        logger.warning(
            "Catalog refresh failed; serving %d cached items and retrying in %ds",
            len(self._cache),
            REFRESH_RETRY_SECONDS,
        )
        self._cache_expires_at = now + REFRESH_RETRY_SECONDS
        return self._cache

    @staticmethod
    def _normalize_kind_includes(include_kinds: list[str] | None) -> set[str]:
        allowed = {"episode", "film"}
        if include_kinds is None:
            return {"episode", "film"}
        normalized = {
            value.strip().lower()
            for value in include_kinds
            if value and value.strip().lower() in allowed
        }
        return normalized

    @staticmethod
    def _normalize_series_exclusions(exclude_series: list[str] | None) -> set[str]:
        if not exclude_series:
            return set()
        return {
            value.strip().lower() for value in exclude_series if value and value.strip()
        }

    @staticmethod
    def _normalize_film_era_exclusions(excluded_eras: list[str] | None) -> set[str]:
        allowed = {"tos", "tng", "kelvin", "other"}
        if not excluded_eras:
            return set()
        return {
            value.strip().lower()
            for value in excluded_eras
            if value and value.strip().lower() in allowed
        }

    @staticmethod
    def _filter_catalog(
        catalog: list[CatalogItem],
        *,
        included_kinds: set[str],
        excluded_series: set[str],
        excluded_film_eras: set[str],
        include_unaired: bool,
        exclude_non_canon: bool,
    ) -> list[CatalogItem]:
        today = date.today()
        return [
            item
            for item in catalog
            if item.kind in included_kinds
            and item.series.lower() not in excluded_series
            and not (
                item.kind == "film"
                and item.film_era is not None
                and item.film_era in excluded_film_eras
            )
            and (item.canon or not exclude_non_canon)
            and (
                include_unaired
                or (item.kind == "film" and item.air_date is None)
                or (item.air_date is not None and item.air_date <= today)
            )
        ]

    async def get_series_options(self) -> list[str]:
        catalog = await self.get_catalog()
        return sorted({item.series for item in catalog})

    async def get_filter_stats(self) -> dict[str, object]:
        catalog = await self.get_catalog()
        today = date.today()
        kind_counts = Counter(item.kind for item in catalog)
        series_counts = Counter(item.series for item in catalog)
        film_era_counts = Counter(
            item.film_era or "unknown" for item in catalog if item.kind == "film"
        )
        non_canon_count = sum(1 for item in catalog if not item.canon)
        unaired_count = sum(
            1
            for item in catalog
            if item.air_date is not None and item.air_date > today
        )

        return {
            "total": len(catalog),
            "episodes": kind_counts.get("episode", 0),
            "films": kind_counts.get("film", 0),
            "non_canon": non_canon_count,
            "unaired": unaired_count,
            "series_counts": dict(series_counts),
            "film_era_counts": {
                "tos": film_era_counts.get("tos", 0),
                "tng": film_era_counts.get("tng", 0),
                "kelvin": film_era_counts.get("kelvin", 0),
                "other": film_era_counts.get("other", 0)
                + film_era_counts.get("unknown", 0),
            },
        }

    async def get_pool_counts(
        self,
        *,
        include_kinds: list[str] | None = None,
        exclude_series: list[str] | None = None,
        exclude_film_eras: list[str] | None = None,
        include_unaired: bool = False,
        exclude_non_canon: bool = False,
    ) -> dict[str, int]:
        catalog = await self.get_catalog()
        normalized_included_kinds = self._normalize_kind_includes(include_kinds)
        normalized_excluded_series = self._normalize_series_exclusions(exclude_series)
        normalized_excluded_eras = self._normalize_film_era_exclusions(
            exclude_film_eras
        )
        filtered = self._filter_catalog(
            catalog,
            included_kinds=normalized_included_kinds,
            excluded_series=normalized_excluded_series,
            excluded_film_eras=normalized_excluded_eras,
            include_unaired=include_unaired,
            exclude_non_canon=exclude_non_canon,
        )

        total_available = len(catalog)
        total_selected = len(filtered)
        episodes_available = sum(1 for item in catalog if item.kind == "episode")
        episodes_selected = sum(1 for item in filtered if item.kind == "episode")
        films_available = sum(1 for item in catalog if item.kind == "film")
        films_selected = sum(1 for item in filtered if item.kind == "film")

        return {
            "total_available": total_available,
            "total_selected": total_selected,
            "episodes_available": episodes_available,
            "episodes_selected": episodes_selected,
            "films_available": films_available,
            "films_selected": films_selected,
        }

    async def get_random_item(
        self,
        *,
        include_kinds: list[str] | None = None,
        exclude_series: list[str] | None = None,
        exclude_film_eras: list[str] | None = None,
        include_unaired: bool = False,
        exclude_non_canon: bool = False,
    ) -> tuple[CatalogItem, int]:
        catalog = await self.get_catalog()
        normalized_included_kinds = self._normalize_kind_includes(include_kinds)
        normalized_excluded_series = self._normalize_series_exclusions(exclude_series)
        normalized_excluded_eras = self._normalize_film_era_exclusions(
            exclude_film_eras
        )
        filtered = self._filter_catalog(
            catalog,
            included_kinds=normalized_included_kinds,
            excluded_series=normalized_excluded_series,
            excluded_film_eras=normalized_excluded_eras,
            include_unaired=include_unaired,
            exclude_non_canon=exclude_non_canon,
        )
        if not filtered:
            raise ValueError("No matches for the selected filters.")
        return random.choice(filtered), len(filtered)

    async def get_release_timeline(
        self,
        *,
        include_kinds: list[str] | None = None,
        exclude_series: list[str] | None = None,
        exclude_film_eras: list[str] | None = None,
        include_unaired: bool = False,
        exclude_non_canon: bool = False,
    ) -> dict[str, object]:
        catalog = await self.get_catalog()
        normalized_included_kinds = self._normalize_kind_includes(include_kinds)
        normalized_excluded_series = self._normalize_series_exclusions(exclude_series)
        normalized_excluded_eras = self._normalize_film_era_exclusions(
            exclude_film_eras
        )
        filtered = self._filter_catalog(
            catalog,
            included_kinds=normalized_included_kinds,
            excluded_series=normalized_excluded_series,
            excluded_film_eras=normalized_excluded_eras,
            include_unaired=include_unaired,
            exclude_non_canon=exclude_non_canon,
        )

        by_year = Counter(item.year for item in filtered if item.year is not None)
        sorted_years = sorted(by_year.keys())

        if sorted_years:
            start_year = sorted_years[0]
            end_year = sorted_years[-1]
            sorted_buckets = [
                {"year": year, "count": by_year.get(year, 0)}
                for year in range(start_year, end_year + 1)
            ]
        else:
            sorted_buckets = []

        total_selected = len(filtered)
        total_with_year = sum(by_year.values())
        return {
            "total_selected": total_selected,
            "total_with_year": total_with_year,
            "total_without_year": total_selected - total_with_year,
            "buckets": sorted_buckets,
        }

    async def search_catalog(
        self,
        *,
        query: str,
        include_kinds: list[str] | None = None,
        exclude_series: list[str] | None = None,
        exclude_film_eras: list[str] | None = None,
        include_unaired: bool = False,
        exclude_non_canon: bool = False,
        limit: int = 100,
    ) -> tuple[list[CatalogItem], int]:
        catalog = await self.get_catalog()
        normalized_included_kinds = self._normalize_kind_includes(include_kinds)
        normalized_excluded_series = self._normalize_series_exclusions(exclude_series)
        normalized_excluded_eras = self._normalize_film_era_exclusions(
            exclude_film_eras
        )
        filtered_catalog = self._filter_catalog(
            catalog,
            included_kinds=normalized_included_kinds,
            excluded_series=normalized_excluded_series,
            excluded_film_eras=normalized_excluded_eras,
            include_unaired=include_unaired,
            exclude_non_canon=exclude_non_canon,
        )

        def chronology_key(item: CatalogItem) -> tuple[int, int, int, str, str]:
            # Unknown years go last to keep chronological ordering stable.
            year = item.year if item.year is not None else 9999
            season = item.season if item.season is not None else 0
            episode = item.episode_number if item.episode_number is not None else 0
            return (year, season, episode, item.series.lower(), item.title.lower())

        normalized_query = query.strip().lower()
        if not normalized_query:
            chronological = sorted(
                filtered_catalog,
                key=chronology_key,
            )
            total_hits = len(chronological)
            return chronological[: min(limit, 100)], total_hits

        def score(item: CatalogItem) -> int:
            title = item.title.lower()
            series = item.series.lower()
            year_text = str(item.year) if item.year is not None else ""
            combined = f"{series} {title} {year_text}".strip()
            score_value = 0
            if normalized_query in title:
                score_value += 5
            if normalized_query in series:
                score_value += 4
            if year_text and normalized_query in year_text:
                score_value += 4
            for token in normalized_query.split():
                if token in combined:
                    score_value += 1
            return score_value

        ranked = [item for item in filtered_catalog if score(item) > 0]
        ranked.sort(key=lambda item: chronology_key(item))

        total_hits = len(ranked)
        return ranked[:limit], total_hits


catalog_service = CatalogService()
