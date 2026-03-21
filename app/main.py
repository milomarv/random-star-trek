from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.catalog_config import SERIES_ABBREVIATIONS
from app.models import (
    FilterState,
    PoolCountsResponse,
    RandomPickResponse,
    ReleaseTimelineResponse,
    SearchHitResponse,
    SearchResponse,
)
from app.service import catalog_service
from app.settings import settings

app = FastAPI(title=settings.app_title)
templates = Jinja2Templates(directory="app/templates")

_FILTERS_FILE = Path("data/filters_state.json")


def _with_base(path: str) -> str:
    base = settings.normalized_base_path
    if not base:
        return path
    return f"{base}{path}"


app.mount(_with_base("/static"), StaticFiles(directory="app/static"), name="static")


@app.get(_with_base("/"), response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    series_options = await catalog_service.get_series_options()
    filter_stats = await catalog_service.get_filter_stats()
    pool_counts = await catalog_service.get_pool_counts()
    context = {
        "request": request,
        "base_path": settings.normalized_base_path,
        "series_options": series_options,
        "series_abbreviations": SERIES_ABBREVIATIONS,
        "filter_stats": filter_stats,
        "pool_counts": pool_counts,
        "persist_filters": settings.persist_filters,
    }
    return templates.TemplateResponse(request, "index.html", context)


@app.get(_with_base("/api/filters"), response_model=FilterState)
async def get_filter_state() -> FilterState:
    if not settings.persist_filters:
        raise HTTPException(status_code=404, detail="Filter persistence not enabled")
    if _FILTERS_FILE.exists():
        try:
            return FilterState.model_validate(json.loads(_FILTERS_FILE.read_text()))
        except Exception:
            pass
    return FilterState()


@app.post(_with_base("/api/filters"), response_model=FilterState)
async def save_filter_state(state: FilterState) -> FilterState:
    if not settings.persist_filters:
        raise HTTPException(status_code=404, detail="Filter persistence not enabled")
    _FILTERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _FILTERS_FILE.write_text(state.model_dump_json())
    return state


@app.get(_with_base("/api/pool-stats"), response_model=PoolCountsResponse)
async def pool_stats(
    include_kinds: list[str] | None = Query(default=None, alias="include_kinds"),
    exclude_series: list[str] | None = Query(default=None, alias="exclude_series"),
    exclude_film_eras: list[str] | None = Query(
        default=None, alias="exclude_film_eras"
    ),
) -> PoolCountsResponse:
    return PoolCountsResponse(
        **await catalog_service.get_pool_counts(
            include_kinds=include_kinds,
            exclude_series=exclude_series,
            exclude_film_eras=exclude_film_eras,
        )
    )


@app.get(_with_base("/api/random"), response_model=RandomPickResponse)
async def random_pick(
    include_kinds: list[str] | None = Query(default=None, alias="include_kinds"),
    exclude_series: list[str] | None = Query(default=None, alias="exclude_series"),
    exclude_film_eras: list[str] | None = Query(
        default=None, alias="exclude_film_eras"
    ),
) -> RandomPickResponse:
    try:
        item, total = await catalog_service.get_random_item(
            include_kinds=include_kinds,
            exclude_series=exclude_series,
            exclude_film_eras=exclude_film_eras,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RandomPickResponse(item=item, total_candidates=total)


@app.get(_with_base("/api/search"), response_model=SearchResponse)
async def search_items(
    q: str = "",
    include_kinds: list[str] | None = Query(default=None, alias="include_kinds"),
    exclude_series: list[str] | None = Query(default=None, alias="exclude_series"),
    exclude_film_eras: list[str] | None = Query(
        default=None, alias="exclude_film_eras"
    ),
) -> SearchResponse:
    hits, total_hits = await catalog_service.search_catalog(
        query=q,
        include_kinds=include_kinds,
        exclude_series=exclude_series,
        exclude_film_eras=exclude_film_eras,
        limit=100,
    )
    return SearchResponse(
        query=q,
        total_hits=total_hits,
        hits=[
            SearchHitResponse(
                series=item.series,
                title=item.title,
                year=item.year,
                season=item.season,
                episode=item.episode_number,
                type=item.kind,
                prime_video_url=item.prime_video_url,
            )
            for item in hits
        ],
    )


@app.get(_with_base("/api/release-timeline"), response_model=ReleaseTimelineResponse)
async def release_timeline(
    include_kinds: list[str] | None = Query(default=None, alias="include_kinds"),
    exclude_series: list[str] | None = Query(default=None, alias="exclude_series"),
    exclude_film_eras: list[str] | None = Query(
        default=None, alias="exclude_film_eras"
    ),
) -> ReleaseTimelineResponse:
    payload = await catalog_service.get_release_timeline(
        include_kinds=include_kinds,
        exclude_series=exclude_series,
        exclude_film_eras=exclude_film_eras,
    )
    return ReleaseTimelineResponse.model_validate(payload)


@app.get(_with_base("/partials/random-card"), response_class=HTMLResponse)
async def random_card(
    request: Request,
    include_kinds: list[str] | None = Query(default=None, alias="include_kinds"),
    exclude_series: list[str] | None = Query(default=None, alias="exclude_series"),
    exclude_film_eras: list[str] | None = Query(
        default=None, alias="exclude_film_eras"
    ),
) -> HTMLResponse:
    try:
        item, total = await catalog_service.get_random_item(
            include_kinds=include_kinds,
            exclude_series=exclude_series,
            exclude_film_eras=exclude_film_eras,
        )
    except ValueError:
        context = {
            "request": request,
            "base_path": settings.normalized_base_path,
            "include_kinds": include_kinds or [],
            "exclude_series": exclude_series or [],
            "exclude_film_eras": exclude_film_eras or [],
        }
        return templates.TemplateResponse(request, "partials/no_result.html", context)

    context = {
        "request": request,
        "base_path": settings.normalized_base_path,
        "item": item,
        "series_abbreviations": SERIES_ABBREVIATIONS,
        "total": total,
        "include_kinds": include_kinds or [],
        "exclude_series": exclude_series or [],
        "exclude_film_eras": exclude_film_eras or [],
    }
    return templates.TemplateResponse(request, "partials/random_card.html", context)
