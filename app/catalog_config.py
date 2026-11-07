from __future__ import annotations

TVMAZE_SINGLESEARCH_URL = "https://api.tvmaze.com/singlesearch/shows?q={query}"
TVMAZE_EPISODES_URL = "https://api.tvmaze.com/shows/{show_id}/episodes"
TMDB_API_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w1280"
TMDB_FILM_COLLECTION_IDS: tuple[int, ...] = (151, 115570, 115575)
TMDB_EXTRA_FILM_QUERIES: tuple[str, ...] = ("Star Trek: Section 31",)

CANONICAL_SERIES_QUERIES: tuple[str, ...] = (
    "Star Trek: The Original Series",
    "Star Trek: The Animated Series",
    "Star Trek: The Next Generation",
    "Star Trek: Deep Space Nine",
    "Star Trek: Voyager",
    "Star Trek: Enterprise",
    "Star Trek: Discovery",
    "Star Trek: Short Treks",
    "Star Trek: very Short Treks",
    "Star Trek: Picard",
    "Star Trek: Lower Decks",
    "Star Trek: Prodigy",
    "Star Trek: Strange New Worlds",
    "Star Trek: Starfleet Academy",
)

FAN_SERIES_QUERIES: tuple[str, ...] = (
    "Star Trek Continues",
    "Star Trek: Odyssey",
    "Star Trek: Scouts",
    "Star Trek: Renegades",
)

YOUTUBE_FALLBACK_SERIES: set[str] = {
    "star trek continues",
    "star trek: odyssey",
    "star trek odyssey",
    "star trek: renegades",
    "star trek renegades",
    "star trek: scouts",
    "star trek scouts",
}

SERIES_NAME_OVERRIDES: dict[str, str] = {
    "star trek": "Star Trek: The Original Series",
}

SERIES_ABBREVIATIONS: dict[str, str] = {
    "star trek: the original series": "TOS",
    "star trek: the animated series": "TAS",
    "star trek: the next generation": "TNG",
    "star trek: deep space nine": "DS9",
    "star trek: voyager": "VOY",
    "star trek: enterprise": "ENT",
    "star trek: discovery": "DIS",
    "star trek: short treks": "ST",
    "star trek: very short treks": "vST",
    "star trek: picard": "PIC",
    "star trek: lower decks": "LD",
    "star trek: prodigy": "PRO",
    "star trek: strange new worlds": "SNW",
    "star trek: starfleet academy": "SFA",
    "star trek continues": "STC",
    "star trek: odyssey": "ODY",
    "star trek odyssey": "ODY",
    "star trek: renegades": "REN",
    "star trek renegades": "REN",
    "star trek: scouts": "SCT",
    "star trek scouts": "SCT",
}
