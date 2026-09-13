from __future__ import annotations

import sys
from collections import Counter

import config
from csv_store import write_csv
from uit_scraper import scrape


def main() -> int:
    print("Brugge Film Tool — UiTinVlaanderen")
    print(f"Zoekt {config.WINDOW_DAYS} dagen vooruit in Brugge ({config.BRUGGE_NIS_CODE}).")

    try:
        events = scrape()
    except Exception as exc:
        print(f"Fout bij ophalen van UiTinVlaanderen: {exc}")
        return 1

    write_csv(config.OUTPUT_CSV, events)
    counts = Counter(e.category for e in events)
    parts = [f"{counts[name]} {name.lower()}" for name in sorted(counts)]

    print(f"Gevonden: {len(events)} event(s) — " + ", ".join(parts) + ".")
    print(f"CSV geschreven naar: {config.OUTPUT_CSV.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
