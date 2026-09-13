# Brugge Film Tool — versie 0.1

Volledig losstaand proefproject. Het wijzigt niets aan de bestaande concerttool.

## Wat doet deze versie?

- Bevraagt alleen UiTinVlaanderen.
- Beperkt de zoekopdracht tot Brugge via NIS-code `nis-31005`.
- Neemt alle evenementen van UiT-type **Film** (`0.50.6.0.0`) mee.
- Bekijkt daarnaast een beperkte groep andere UiT-eventtypes (festival, lezing, workshop, lessenreeks, concert en tentoonstelling) en houdt daar alleen events van bij wanneer titel of beschrijving filmgerelateerde woorden bevat.
- Dubbels uit beide zoekrondes worden verwijderd op UiT-event-ID.
- Schrijft alles chronologisch naar `data/brugge_film_events.csv`.

## CSV-kolommen

- Date
- Start Time
- Title
- Venue
- Category (`Film` of `Filmgerelateerd`)
- Description
- UiT Event Link
- UiT Event ID

## Installeren op Windows

1. Installeer Python 3.11 of nieuwer als dat nog niet aanwezig is.
2. Dubbelklik `install_windows.bat`.
3. Dubbelklik daarna `run_windows.bat`.

Of vanuit Command Prompt / PowerShell:

```text
python -m pip install -r requirements.txt
python main.py
```

## Instellingen

In `config.py` kan je onder meer aanpassen:

- `WINDOW_DAYS`: standaard 120 dagen vooruit.
- `FILM_KEYWORDS`: woorden waarmee niet-filmtypes alsnog als filmgerelateerd worden herkend.
- `RELATED_EVENT_TYPE_IDS`: welke andere UiT-eventtypes als kandidaat worden bekeken.

## Belangrijk in versie 0.1

De directe Film-selectie is betrouwbaar gebaseerd op het officiële UiT-eventtype Film. De categorie `Filmgerelateerd` is bewust een brede trefwoordenfilter. We verzamelen liever eerst iets te veel en verfijnen daarna, in plaats van relevante activiteiten al bij de bron weg te gooien.

De code is syntactisch/testbaar zonder de oude muziektool. Een echte live-run moet op een computer met internet gebeuren; de uitvoeromgeving waarin deze versie gebouwd werd kon de UiTinVlaanderen-host niet rechtstreeks benaderen.

## Lokale browser op macOS

Vanaf v0.2 bevat de tool ook een lokale webinterface.

### Snelste manier

Dubbelklik op:

`run_mac.command`

Bij de eerste start wordt automatisch een lokale Python-omgeving aangemaakt en worden de vereiste packages geïnstalleerd. Daarna opent de browser op:

`http://127.0.0.1:8765`

De interface leest `data/brugge_film_events.csv` en laat toe te:

- zoeken op titel, locatie en beschrijving;
- filteren op Film / Filmgerelateerd;
- filteren op locatie;
- filteren op komende 14, 30 of 60 dagen;
- rechtstreeks naar het UiT-event door te klikken;
- de UiTdatabank opnieuw op te halen met **UiT verversen**.

Stop de lokale browser door in het Terminal-venster `Ctrl+C` te drukken.

### Als macOS het .command-bestand blokkeert

Open Terminal, ga naar de projectmap en voer één keer uit:

```bash
chmod +x run_mac.command
./run_mac.command
```

## v0.6 categorisatie

De categorisatie gebruikt nu niet alleen het UiT-eventtype maar ook titel en beschrijving.
Daardoor kan een event zoals **STOM! FESTIVAL** als **Filmfestival** worden herkend, ook
wanneer UiT het umbrella-event onder een ander eventtype registreert.

Extra categorieën:
- Filmfestival
- Audiovisuele tentoonstelling
- Filmlezing / gesprek
- Filmworkshop
- Filmconcert / live soundtrack
- Filmgerelateerd


Update in v0.6: cinematische film-skin voor de lokale browserinterface.


## v0.6

- Skin-kiezer met vier blijvende thema's: Cinema Noir, Arthouse, Retro 70s en Genre Night.
- De gekozen skin wordt lokaal in de browser onthouden.
- `première`/`premiere` geldt niet langer op zichzelf als filmsignaal; dit voorkomt concert-false-positives zoals een album première.


## v0.8
Nieuwe skin **UiT in Brugge** toegevoegd aan de bestaande skin-selector. Deze skin gebruikt een lichte agenda-grid, filterchips en sortering. De andere skins blijven behouden.

## iPhone gebruiken

Vanaf v0.10 is er een aparte `run_iphone.command`.

1. Zet Mac en iPhone op hetzelfde wifi-netwerk.
2. Dubbelklik `run_iphone.command` op de Mac.
3. Terminal toont een regel zoals `iPhone: http://192.168.1.23:8765`.
4. Open dat adres in Safari op de iPhone.
5. Tik Deel -> Zet op beginscherm.

De Film Tool verschijnt daarna als icoon op het beginscherm en opent in een app-achtige weergave.
De Mac moet aan staan en `run_iphone.command` moet actief zijn zolang de iPhone deze lokale versie gebruikt.


## v0.10 – echte UiT-afbeeldingen
De scraper haalt voor geselecteerde events de officiële afbeelding van de UiT-detailpagina op (og:image), bewaart de URL in de CSV en toont die in de UiT in Brugge-skin. Een lokale image_cache.json voorkomt dat reeds gevonden beelden bij elke refresh opnieuw opgezocht moeten worden.

## v0.16 — iPhone polish

De mobiele interface is aangepast voor iPhone: compacte header, een vaste onderbalk met Filters / Skin / Boven, filters als mobiel bottom-sheet, grotere tikvlakken, horizontaal veegbare categoriechips en geoptimaliseerde kaart- en beeldverhoudingen. Desktopgedrag en scraperlogica blijven ongewijzigd.


## v0.16
De skin **UiT in Brugge** is verder afgestemd op de publieke UiTkalender: witte achtergrond, vlakkere kaarten, eenvoudigere typografie en de informatievolgorde beeld → datum → thema → titel → locatie → Lees meer. De overige skins zijn ongewijzigd.


Update v0.16: UiT in Brugge-skin toont datum als visuele strook op de eventfoto, dichter bij de echte UiTkalender.


Update in v0.16: UiT in Brugge-datumbadge bovenaan het beeld, gebaseerd op de herkenbare dag/maand-badge van de UiTkalender.


Update in v0.16: UiT in Brugge-datumbadge volledig wit en vorm verfijnd naar het kenmerkende label.


Update v0.17: UiT in Brugge-datumbadge opnieuw opgebouwd op basis van de exacte contour uit het aangeleverde referentiebeeld.

## v0.18
Dubbele UiT-records voor dezelfde feitelijke vertoning worden samengevoegd op basis van locatie, datum, startuur en sterk overeenkomende titel. Verschillende dagen, uren en verschillende films blijven afzonderlijk zichtbaar.


## v0.20
Nieuwe optionele skin **Razor Reel**, geïnspireerd op de huidige look & feel van razorreel.com: zwart/wit, Razor Reel-oranje, zware typografie en een beeldgestuurde festivalgrid. Bestaande skins blijven behouden.


Update in v0.22: Genre Night-skin kreeg een donkere kaiju/monster-achtergrond met leesbare overlay.
