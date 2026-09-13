# Publieke Brugge Film Tool op Render

Deze versie kan lokaal blijven draaien, maar is ook voorbereid voor een publieke URL.

## Wat een bezoeker kan doen

- de agenda bekijken op één vaste URL;
- zelf een skin kiezen; die voorkeur wordt lokaal in de browser onthouden;
- op **UiT verversen** klikken. De centrale agenda wordt dan voor iedereen vernieuwd;
- meerdere bezoekers kunnen niet tegelijk dezelfde scrape starten;
- na een refresh geldt standaard 10 minuten cooldown.

## Render

1. Zet deze projectmap in een GitHub-repository.
2. Maak op Render een nieuwe **Web Service** en koppel die repository.
3. Render kan `render.yaml` gebruiken. Anders stel je handmatig in:
   - Build command: `pip install -r requirements.txt`
   - Start command: `python browser.py`
4. De app gebruikt automatisch de door Render aangeleverde `PORT` en bindt op `0.0.0.0`.
5. Na deployment krijg je een publieke `*.onrender.com` URL.

## Data op een gratis Render-service

De lokale filesystemcache is tijdelijk. Na een cold start/restart kan de CSV verdwenen zijn.
De app merkt dat en bouwt de UiT-data automatisch opnieuw op in de achtergrond. Tijdens die eerste opbouw kan de pagina even melden dat de agenda wordt opgebouwd.

Voor een stabiele productie-opstelling zonder heropbouw na restarts kun je later een persistent disk of externe datastore toevoegen.

## Optionele instellingen

- `BRUGGE_FILM_AUTO_REFRESH_HOURS=6`
- `BRUGGE_FILM_REFRESH_COOLDOWN_SECONDS=600`

De skins blijven client-side via `localStorage`; gebruiker A kan dus Razor Reel kiezen terwijl gebruiker B UiT in Brugge kiest.
