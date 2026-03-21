from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class CatalogItem(BaseModel):
    kind: Literal["episode", "film"]
    title: str
    series: str
    season: int | None = None
    episode_number: int | None = None
    year: int | None = None
    film_era: Literal["tos", "tng", "kelvin", "other"] | None = None
    banner_url: str | None = None
    prime_video_url: str


class RandomPickResponse(BaseModel):
    item: CatalogItem
    total_candidates: int


class PoolCountsResponse(BaseModel):
    total_available: int
    total_selected: int
    episodes_available: int
    episodes_selected: int
    films_available: int
    films_selected: int


class SearchHitResponse(BaseModel):
    series: str
    title: str
    year: int | None = None
    season: int | None = None
    episode: int | None = None
    type: Literal["episode", "film"]
    prime_video_url: str


class SearchResponse(BaseModel):
    query: str
    total_hits: int
    hits: list[SearchHitResponse]


class FilterState(BaseModel):
    include_kinds: list[str] = ["episode", "film"]
    exclude_series: list[str] = []
    exclude_film_eras: list[str] = []


class YearBucketResponse(BaseModel):
    year: int
    count: int


class ReleaseTimelineResponse(BaseModel):
    total_selected: int
    total_with_year: int
    total_without_year: int
    buckets: list[YearBucketResponse]
