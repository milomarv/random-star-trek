from __future__ import annotations

TVMAZE_SEARCH_URL = "https://api.tvmaze.com/search/shows?q=star%20trek"
TVMAZE_SINGLESEARCH_URL = "https://api.tvmaze.com/singlesearch/shows?q={query}"
TVMAZE_EPISODES_URL = "https://api.tvmaze.com/shows/{show_id}/episodes"
WIKIPEDIA_CATEGORY_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
WIKIPEDIA_FILM_ROOT_CATEGORY = "Category:Star Trek (film franchise)"

CANONICAL_SERIES_QUERIES: tuple[str, ...] = (
    "Star Trek: The Original Series",
    "Star Trek: The Animated Series",
    "Star Trek: The Next Generation",
    "Star Trek: Deep Space Nine",
    "Star Trek: Voyager",
    "Star Trek: Enterprise",
    "Star Trek: Discovery",
    "Star Trek: Short Treks",
    "Star Trek: Picard",
    "Star Trek: Lower Decks",
    "Star Trek: Prodigy",
    "Star Trek: Strange New Worlds",
    "Star Trek: Starfleet Academy",
)

EXCLUDED_FILM_TITLES: set[str] = {
    "star trek: the god thing",
    "star trek: planet of the titans",
}

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
