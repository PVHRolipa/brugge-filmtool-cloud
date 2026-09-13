from datetime import date

import uit_scraper


def fake_fetch(today, event_type_ids):
    event_type = event_type_ids[0]

    if event_type == "0.50.6.0.0":
        return [
            {
                "id": "film-1",
                "name": "Voorbeeldfilm",
                "description": "<p>Een filmvertoning in Brugge.</p>",
                "location": {"name": "Voorbeeldzaal"},
                "calendar": {"startDate": "2026-10-01T18:00:00.000Z"},
            },
            {
                "id": "darkside-a",
                "name": "The Dark Side of the Moon",
                "description": "Planetariumfilm met muziek van Pink Floyd.",
                "location": {"name": "Cozmix - Volkssterrenwacht Beisbroek"},
                "calendar": {"startDate": "2026-10-24T18:00:00.000Z"},
            },
            {
                "id": "darkside-b",
                "name": "Nocturne: The Dark Side of the Moon",
                "description": "Een bijzondere nocturne van de planetariumfilm met muziek van Pink Floyd en extra omkadering.",
                "location": {"name": "Cozmix - Volkssterrenwacht Beisbroek"},
                "calendar": {"startDate": "2026-10-24T18:00:00.000Z"},
            },
            {
                "id": "different-film",
                "name": "Moonage Daydream",
                "description": "Een andere film die toevallig op hetzelfde moment start.",
                "location": {"name": "Cozmix - Volkssterrenwacht Beisbroek"},
                "calendar": {"startDate": "2026-10-24T18:00:00.000Z"},
            },
            {
                # Deliberately NOT Festival-typed: the content must still upgrade it.
                "id": "stom-1",
                "name": "STOM! FESTIVAL",
                "description": "Het festival van de stille film met live muziek.",
                "location": {"name": "Cinema Lumière Brugge"},
                "calendar": {"startDate": "2026-09-17T18:00:00.000Z"},
            },
        ]

    if event_type == "0.0.0.0.0":
        return [{
            "id": "expo-1",
            "name": "AiR Biekorf 11.0: Dysencryption - Arjan Vanmeenen",
            "description": "Een audiovisuele tentoonstelling met videoproductie en projectie.",
            "location": {"name": "Biekorf"},
            "calendar": {"startDate": "2026-09-20T00:00:00.000Z"},
        }]

    if event_type == "0.3.2.0.0":
        return [{
            "id": "lecture-1",
            "name": "Lezing over de geschiedenis van cinema",
            "description": "Een gesprek met een filmmaker.",
            "location": {"name": "Voorbeeldlocatie"},
            "calendar": {"startDate": "2026-10-03T17:30:00.000Z"},
        }]

    if event_type == "0.50.4.0.0":
        return [
            {
                "id": "concert-1",
                "name": "Nosferatu live",
                "description": "Filmconcert met live soundtrack bij de stille film.",
                "location": {"name": "Voorbeeldlocatie"},
                "calendar": {"startDate": "2026-10-04T18:00:00.000Z"},
            },
            {
                "id": "bard-1",
                "name": "Album premiere Bard Hartman",
                "description": "Debuutalbum voor het eerst live met full band. Beleef deze première van dichtbij!",
                "location": {"name": "CC De Dijk"},
                "calendar": {"startDate": "2026-10-03T14:30:00.000Z"},
            },
            {
                "id": "poets-1",
                "name": "Only The Poets + Alex Spencer",
                "description": "Alt-pop en indierock. Alex Spencer kreeg een plek op de soundtrack van EA SPORTS FC 25.",
                "location": {"name": "Cactus Muziekcentrum"},
                "calendar": {"startDate": "2026-09-27T17:30:00.000Z"},
            },
            {
                "id": "sergeant-1",
                "name": "Sergeant + Klein Volk",
                "description": "Experimentele pop met filmmaker/componist Benjamin Cools en verwijzingen naar pellicule.",
                "location": {"name": "Cactus Muziekcentrum"},
                "calendar": {"startDate": "2026-09-27T17:30:00.000Z"},
            },
        ]

    return []


uit_scraper._fetch_events = fake_fetch
uit_scraper._enrich_images = lambda events: events

html = '<html><head><meta property="og:image" content="https://images.example/poster.jpg"></head></html>'
assert uit_scraper._extract_image_url(html, "https://www.uitinvlaanderen.be/example") == "https://images.example/poster.jpg"

events = uit_scraper.scrape(date(2026, 9, 12))
by_id = {e.event_id: e for e in events}

assert by_id["film-1"].category == "Film"
# Duplicate records for one actual performance collapse to one, while another
# simultaneous film at the same venue is preserved. The richer title wins.
darkside = [e for e in events if "dark side of the moon" in e.title.casefold()]
assert len(darkside) == 1
assert darkside[0].event_id == "darkside-b"
assert "different-film" in by_id
assert by_id["stom-1"].category == "Filmfestival"
assert by_id["expo-1"].category == "Audiovisuele tentoonstelling"
assert by_id["lecture-1"].category == "Filmlezing / gesprek"
assert by_id["concert-1"].category == "Filmconcert / live soundtrack"
assert "bard-1" not in by_id
assert "poets-1" not in by_id
assert "sergeant-1" not in by_id
print("Offline test OK")
