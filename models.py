from dataclasses import dataclass
from datetime import date, time


@dataclass(frozen=True)
class FilmEvent:
    event_id: str
    date: date
    start_time: time | None
    title: str
    venue: str
    category: str
    description: str
    event_link: str
    image_url: str = ""
