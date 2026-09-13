import csv
from pathlib import Path

from models import FilmEvent

CSV_HEADER = [
    "Date",
    "Start Time",
    "Title",
    "Venue",
    "Category",
    "Description",
    "UiT Event Link",
    "UiT Event ID",
    "Image URL",
]


def write_csv(path: Path, events: list[FilmEvent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for event in events:
            writer.writerow([
                event.date.isoformat(),
                event.start_time.strftime("%H:%M") if event.start_time else "",
                event.title,
                event.venue,
                event.category,
                event.description,
                event.event_link,
                event.event_id,
                event.image_url,
            ])
