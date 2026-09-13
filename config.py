from pathlib import Path

BRUGGE_NIS_CODE = "nis-31005"
WINDOW_DAYS = 120
PAGE_SIZE = 50
TIMEOUT = 15
OUTPUT_CSV = Path("data/brugge_film_events.csv")

# Official UiTdatabank event type for Film.
FILM_EVENT_TYPE_ID = "0.50.6.0.0"

# Secondary types worth checking for film-related side events. These events
# are only kept when their title/description contains a film-related keyword.
RELATED_EVENT_TYPE_IDS = (
    "0.5.0.0.0",   # Festival
    "0.3.2.0.0",   # Lezing of congres
    "0.3.1.0.1",   # Cursus met open sessie / workshop
    "0.3.1.0.0",   # Lessenreeks
    "0.50.4.0.0",  # Concert (e.g. film concert / live soundtrack)
    "0.0.0.0.0",   # Tentoonstelling
)

FILM_KEYWORDS = (
    "film", "films", "cinema", "bioscoop", "kortfilm", "kortfilms",
    "documentaire", "documentaires", "filmfestival",
    "screening", "vertoning", "vertoningen",
    "animatiefilm", "filmlezing", "filmconcert", "filmmuziek",
    "soundtrack", "regisseur", "cineast", "filmmaker", "filmclub",
    "filmquiz", "filmworkshop", "video-essay", "video essay",
)


# Concerts require stronger film evidence than other related event types.
# Generic words such as "soundtrack" or "filmmaker" occur often in ordinary
# music biographies and would otherwise create false positives.
FILM_CONCERT_KEYWORDS = (
    "filmconcert", "film concert", "ciné-concert", "cine-concert", "cineconcert",
    "live soundtrack", "live score", "live film score", "film score live",
    "film met live muziek", "filmvertoning met live muziek",
    "stille film met live muziek", "silent film with live music",
    "live muziek bij de film", "live music to the film",
    "soundtrack live", "soundtrack bij de film",
)

# Stronger signals used for categorisation after an event has already been
# accepted as film-related.
FILM_FESTIVAL_KEYWORDS = (
    "filmfestival", "film festival", "festival van de film",
    "festival van de stille film", "stillefilmfestival",
)

AUDIOVISUAL_EXHIBITION_KEYWORDS = (
    "videokunst", "video-installatie", "video installatie",
    "video installation", "audiovisueel", "audiovisual",
    "moving image", "immersive", "projectie", "videowerk",
    "video work", "videoproductie", "video productie",
)
