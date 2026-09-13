import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

import config
from models import FilmEvent

URL = "https://www.uitinvlaanderen.be/api/graphql"
SITE_BASE_URL = "https://www.uitinvlaanderen.be"
BRUSSELS_TZ = ZoneInfo("Europe/Brussels")
IMAGE_CACHE_PATH = Path(__file__).resolve().parent / "data" / "image_cache.json"
IMAGE_FETCH_WORKERS = 10
IMAGE_TIMEOUT = 8
IMAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.7",
}

# The UiTinVlaanderen GraphQL route is an internal same-origin web endpoint.
# Local requests are accepted fairly liberally, while cloud/datacenter traffic
# may be rejected when it does not resemble the site's normal browser calls.
# Keep these headers close to what the web app itself sends.
API_HEADERS = {
    "User-Agent": IMAGE_HEADERS["User-Agent"],
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "nl-BE,nl;q=0.9,en;q=0.7",
    "Content-Type": "application/json",
    "Origin": SITE_BASE_URL,
    "Referer": f"{SITE_BASE_URL}/agenda",
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}

FESTIVAL_EVENT_TYPE_ID = "0.5.0.0.0"
LECTURE_EVENT_TYPE_ID = "0.3.2.0.0"
WORKSHOP_EVENT_TYPE_IDS = {"0.3.1.0.1", "0.3.1.0.0"}
CONCERT_EVENT_TYPE_ID = "0.50.4.0.0"
EXHIBITION_EVENT_TYPE_ID = "0.0.0.0.0"

SEARCH_QUERY = """
query GetEventSearch($limit: Float, $offset: Float, $eventTypes: [String!], $nisCodes: [String!], $dateFrom: DateTimeISO, $dateTo: DateTimeISO) {
  events(limit: $limit, offset: $offset, eventTypes: $eventTypes, nisCodes: $nisCodes, dateFrom: $dateFrom, dateTo: $dateTo) {
    totalItems
    data {
      ... on Event {
        id
        name
        description
        location { name }
        calendar { startDate }
      }
    }
  }
}
"""




def _load_image_cache() -> dict[str, str]:
    if not IMAGE_CACHE_PATH.exists():
        return {}
    try:
        data = json.loads(IMAGE_CACHE_PATH.read_text(encoding="utf-8"))
        return {str(k): str(v or "") for k, v in data.items()} if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _save_image_cache(cache: dict[str, str]) -> None:
    try:
        IMAGE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        IMAGE_CACHE_PATH.write_text(
            json.dumps(cache, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError:
        # Image caching is an optimisation only; scraping must still succeed.
        pass


def _clean_embedded_url(value: str) -> str:
    # URLs embedded in SSR JSON can be escaped as https:\\/\\/… or with \u0026.
    value = value.strip().strip('"\'')
    value = value.replace("\\/", "/")
    try:
        value = bytes(value, "utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        pass
    return value.replace("&amp;", "&")


def _looks_like_event_image(url: str) -> bool:
    lowered = url.casefold()
    return any(host in lowered for host in (
        "images-prod-uitdatabank.imgix.net",
        "udb-media.imgix.net",
        "udb2-media.imgix.net",
        "io.uitdatabank.be/images/",
    ))


def _extract_image_url(html: str, page_url: str) -> str:
    soup = BeautifulSoup(html, "lxml")

    # First choice: normal social metadata.
    candidates = [
        soup.find("meta", property="og:image:secure_url"),
        soup.find("meta", property="og:image"),
        soup.find("meta", attrs={"name": "twitter:image"}),
        soup.find("meta", attrs={"name": "twitter:image:src"}),
    ]
    for meta in candidates:
        if meta is None:
            continue
        content = _clean_embedded_url(str(meta.get("content") or ""))
        if content:
            return urljoin(page_url, content)

    # UiTinVlaanderen is a headless app. On some event pages the image URL is
    # only present inside server-rendered JSON rather than an og:image tag.
    # Search the raw HTML for known UiTdatabank media hosts as a robust fallback.
    normalized_html = html.replace("\\/", "/").replace("\\u0026", "&").replace("\\u002F", "/")
    raw_patterns = (
        r'https?://(?:images-prod-uitdatabank\.imgix\.net|udb-media\.imgix\.net|udb2-media\.imgix\.net)/[^"\'<>\s]+',
        r'https?://io\.uitdatabank\.be/images/[^"\'<>\s]+',
    )
    for pattern in raw_patterns:
        match = re.search(pattern, normalized_html, flags=re.IGNORECASE)
        if match:
            candidate = _clean_embedded_url(match.group(0))
            if _looks_like_event_image(candidate):
                return candidate

    # Last fallback: inspect actual image/link attributes in the parsed page.
    for tag in soup.find_all(["img", "source", "a"]):
        for attr in ("src", "srcset", "href"):
            value = str(tag.get(attr) or "").strip()
            if not value:
                continue
            # srcset can contain multiple URL + width pairs; first URL is enough.
            value = value.split(",", 1)[0].strip().split(" ", 1)[0]
            candidate = urljoin(page_url, _clean_embedded_url(value))
            if _looks_like_event_image(candidate):
                return candidate
    return ""


def _fetch_event_image(event: FilmEvent) -> tuple[str, str]:
    try:
        response = requests.get(
            event.event_link,
            timeout=IMAGE_TIMEOUT,
            headers=IMAGE_HEADERS,
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "html" not in content_type.casefold():
            return event.event_id, ""
        response.encoding = response.encoding or "utf-8"
        return event.event_id, _extract_image_url(response.text, event.event_link)
    except requests.RequestException:
        return event.event_id, ""


def _enrich_images(events: list[FilmEvent]) -> list[FilmEvent]:
    if not events:
        return events

    cache = _load_image_cache()
    missing = [event for event in events if event.event_id not in cache]

    if missing:
        with ThreadPoolExecutor(max_workers=IMAGE_FETCH_WORKERS) as pool:
            futures = [pool.submit(_fetch_event_image, event) for event in missing]
            for future in as_completed(futures):
                event_id, image_url = future.result()
                if image_url:
                    cache[event_id] = image_url
        _save_image_cache(cache)

    return [replace(event, image_url=cache.get(event.event_id, "")) for event in events]




_TITLE_STOPWORDS = {
    "a", "an", "and", "de", "een", "en", "het", "of", "the", "van",
}


def _normalize_title(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _titles_match_for_dedupe(a: str, b: str) -> bool:
    left = _normalize_title(a)
    right = _normalize_title(b)
    if not left or not right:
        return False
    if left == right:
        return True

    # Covers variants such as “Nocturne: The Dark Side of the Moon” versus
    # “The Dark Side of the Moon” without relying on one hard-coded prefix.
    shorter, longer = sorted((left, right), key=len)
    if len(shorter) >= 12 and shorter in longer:
        return True

    left_tokens = {t for t in left.split() if t not in _TITLE_STOPWORDS}
    right_tokens = {t for t in right.split() if t not in _TITLE_STOPWORDS}
    if min(len(left_tokens), len(right_tokens)) < 3:
        return False
    overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
    return overlap >= 0.8


def _duplicate_quality(event: FilmEvent) -> tuple[int, int, int]:
    rank = {
        "Filmgerelateerd": 0,
        "Filmlezing / gesprek": 1,
        "Filmworkshop": 1,
        "Filmconcert / live soundtrack": 1,
        "Audiovisuele tentoonstelling": 1,
        "Film": 2,
        "Filmfestival": 3,
    }
    return (
        rank.get(event.category, 0),
        len(event.description or ""),
        len(event.title or ""),
    )


def _deduplicate_performances(events: list[FilmEvent]) -> list[FilmEvent]:
    """Collapse duplicate UiT records for the same actual performance.

    Different dates and different start times are always preserved. Two events
    are only merged when venue/date/time match and their titles are equal or
    strongly overlap. This prevents simultaneous, genuinely different films at
    a multiplex from being collapsed.
    """
    kept: list[FilmEvent] = []
    for candidate in events:
        duplicate_index = None
        for index, existing in enumerate(kept):
            if (
                existing.date == candidate.date
                and existing.start_time == candidate.start_time
                and _normalize_title(existing.venue) == _normalize_title(candidate.venue)
                and _titles_match_for_dedupe(existing.title, candidate.title)
            ):
                duplicate_index = index
                break

        if duplicate_index is None:
            kept.append(candidate)
            continue

        existing = kept[duplicate_index]
        if _duplicate_quality(candidate) > _duplicate_quality(existing):
            kept[duplicate_index] = candidate

    return kept


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    return slug or "event"


def _detail_page_url(event_id: str, name: str) -> str:
    return f"{SITE_BASE_URL}/agenda/e/{_slugify(name)}/{event_id}"


def _strip_html(html: str) -> str:
    return BeautifulSoup(html, "lxml").get_text(separator=" ", strip=True)


def _date_range(today: date) -> tuple[str, str]:
    cutoff = today + timedelta(days=config.WINDOW_DAYS)
    return (
        f"{today.isoformat()}T00:00:00.000Z",
        f"{cutoff.isoformat()}T23:59:59.999Z",
    )


def _fetch_events(today: date, event_type_ids: list[str] | tuple[str, ...]) -> list[dict]:
    date_from, date_to = _date_range(today)
    items: list[dict] = []
    offset = 0

    while True:
        response = requests.post(
            URL,
            json={
                "query": SEARCH_QUERY,
                "variables": {
                    "limit": config.PAGE_SIZE,
                    "offset": offset,
                    "eventTypes": list(event_type_ids),
                    "nisCodes": [config.BRUGGE_NIS_CODE],
                    "dateFrom": date_from,
                    "dateTo": date_to,
                },
            },
            headers=API_HEADERS,
            timeout=config.TIMEOUT,
        )
        if response.status_code >= 400:
            # Include a short server response in the cloud error. It makes a
            # WAF/proxy rejection distinguishable from a normal API error.
            detail = (response.text or "").strip().replace("\n", " ")[:300]
            raise requests.HTTPError(
                f"{response.status_code} {response.reason} for {URL}"
                + (f" — {detail}" if detail else ""),
                response=response,
            )
        body = response.json()
        if body.get("errors") or body.get("data") is None:
            raise RuntimeError(f"UiTinVlaanderen GraphQL API returned errors: {body.get('errors')}")

        payload = body["data"]["events"]
        page = payload.get("data") or []
        items.extend(page)
        if not page or len(items) >= payload.get("totalItems", 0):
            break
        offset += config.PAGE_SIZE

    return items


def _plain_text(item: dict) -> tuple[str, str]:
    title = str(item.get("name") or "").strip()
    description_html = item.get("description") or ""
    description = _strip_html(description_html) if description_html else ""
    return title, description


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    folded = text.casefold()
    return any(keyword.casefold() in folded for keyword in keywords)


def _contains_film_keyword(title: str, description: str) -> bool:
    return _contains_any(f"{title} {description}", config.FILM_KEYWORDS)


def _looks_like_film_concert(title: str, description: str) -> bool:
    return _contains_any(f"{title} {description}", config.FILM_CONCERT_KEYWORDS)


def _looks_like_film_festival(title: str, description: str) -> bool:
    text = f"{title} {description}"
    if _contains_any(text, config.FILM_FESTIVAL_KEYWORDS):
        return True

    title_folded = title.casefold()
    text_folded = text.casefold()
    # Useful for listings such as "STOM! FESTIVAL" where the description makes
    # the film connection explicit but UiT itself may not use the Festival type.
    return "festival" in title_folded and _contains_film_keyword(title, description)


def _category_for(item: dict, source_event_type: str, default: str) -> str:
    title, description = _plain_text(item)
    text = f"{title} {description}"

    # Content wins over UiT's event type. This catches film festivals even when
    # UiT registered the umbrella event under another type.
    if _looks_like_film_festival(title, description):
        return "Filmfestival"

    if source_event_type == FESTIVAL_EVENT_TYPE_ID:
        return "Filmfestival"

    if source_event_type == EXHIBITION_EVENT_TYPE_ID and _contains_any(
        text, config.AUDIOVISUAL_EXHIBITION_KEYWORDS
    ):
        return "Audiovisuele tentoonstelling"

    if source_event_type == LECTURE_EVENT_TYPE_ID:
        return "Filmlezing / gesprek"

    if source_event_type in WORKSHOP_EVENT_TYPE_IDS:
        return "Filmworkshop"

    if source_event_type == CONCERT_EVENT_TYPE_ID:
        return "Filmconcert / live soundtrack"

    return default


def _parse_datetime(value: str) -> tuple[date, object | None]:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is not None:
        dt = dt.astimezone(BRUSSELS_TZ)
    return dt.date(), dt.time().replace(second=0, microsecond=0, tzinfo=None)


def _to_event(item: dict, category: str) -> FilmEvent | None:
    try:
        title = str(item["name"]).strip()
        event_id = str(item["id"])
        location = item.get("location") or {}
        venue = str(location.get("name") or "").strip()
        start_date = (item.get("calendar") or {}).get("startDate")
        if not start_date:
            return None

        event_date, start_time = _parse_datetime(start_date)
        description_html = item.get("description")
        description = _strip_html(description_html) if description_html else ""

        return FilmEvent(
            event_id=event_id,
            date=event_date,
            start_time=start_time,
            title=title,
            venue=venue,
            category=category,
            description=description,
            event_link=_detail_page_url(event_id, title),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _keep_if_film_related(item: dict, source_event_type: str) -> FilmEvent | None:
    title, description = _plain_text(item)
    text = f"{title} {description}"

    # Concert biographies often contain words such as "soundtrack" or
    # "filmmaker" without the concert itself having any film component. For
    # concerts we therefore require a strong, explicit film-concert signal.
    if source_event_type == CONCERT_EVENT_TYPE_ID:
        if not _looks_like_film_concert(title, description):
            return None
        return _to_event(item, "Filmconcert / live soundtrack")

    # Audiovisual/video exhibitions are relevant even when their text never
    # literally says "film" or "cinema".
    audiovisual_exhibition = (
        source_event_type == EXHIBITION_EVENT_TYPE_ID
        and _contains_any(text, config.AUDIOVISUAL_EXHIBITION_KEYWORDS)
    )

    if not _contains_film_keyword(title, description) and not audiovisual_exhibition:
        return None

    category = _category_for(item, source_event_type, "Filmgerelateerd")
    return _to_event(item, category)


def _prefer(existing: FilmEvent | None, candidate: FilmEvent) -> FilmEvent:
    if existing is None:
        return candidate

    rank = {
        "Filmgerelateerd": 0,
        "Filmlezing / gesprek": 1,
        "Filmworkshop": 1,
        "Filmconcert / live soundtrack": 1,
        "Audiovisuele tentoonstelling": 1,
        "Film": 2,
        "Filmfestival": 3,
    }
    return candidate if rank.get(candidate.category, 0) > rank.get(existing.category, 0) else existing


def scrape(today: date | None = None) -> list[FilmEvent]:
    today = today or date.today()
    by_id: dict[str, FilmEvent] = {}

    # 1. Every event explicitly typed as Film is kept, but content can still
    #    upgrade it to Filmfestival.
    for item in _fetch_events(today, [config.FILM_EVENT_TYPE_ID]):
        category = _category_for(item, config.FILM_EVENT_TYPE_ID, "Film")
        event = _to_event(item, category)
        if event:
            by_id[event.event_id] = _prefer(by_id.get(event.event_id), event)

    # 2. Check each secondary type separately. This lets categorisation use the
    #    source type, while content-based recognition still overrides it.
    for event_type in config.RELATED_EVENT_TYPE_IDS:
        for item in _fetch_events(today, [event_type]):
            event = _keep_if_film_related(item, event_type)
            if event:
                by_id[event.event_id] = _prefer(by_id.get(event.event_id), event)

    events = _deduplicate_performances(list(by_id.values()))
    events = sorted(
        events,
        key=lambda e: (e.date, e.start_time or datetime.min.time(), e.title.casefold()),
    )
    return _enrich_images(events)
