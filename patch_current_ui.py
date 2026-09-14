#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
from datetime import datetime

PROJECT = Path(__file__).resolve().parent
INDEX = PROJECT / "web" / "index.html"
GENRE_BG = PROJECT / "web" / "genre-night-bg.png"

if not INDEX.exists():
    raise SystemExit(f"Niet gevonden: {INDEX}")

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = INDEX.with_name(f"index.backup-{stamp}.html")
shutil.copy2(INDEX, backup)

html = INDEX.read_text(encoding="utf-8")

# 1) Verwijder de refreshknop echt uit de HTML.
html = re.sub(
    r'\s*<button\b[^>]*\bid=["\']refresh["\'][^>]*>.*?</button>',
    '',
    html,
    flags=re.IGNORECASE | re.DOTALL,
)

# 2) Verwijder eventuele JS-listener voor die knop.
html = re.sub(
    r'^\s*(?:if\s*\(\$\(["\']refresh["\']\)\)\s*)?\$\(["\']refresh["\']\)\.addEventListener\(["\']click["\']\s*,\s*refresh\);\s*$',
    '',
    html,
    flags=re.MULTILINE,
)

# 3) Teksten die nog naar handmatig verversen verwijzen neutraliseren.
html = html.replace(
    'Probeer een ruimere periode of haal de UiT-data opnieuw op.',
    'Probeer een ruimere periode of pas je filters aan.'
)
html = html.replace(
    'Nog geen CSV gevonden. Klik op “UiT verversen”.',
    'Nog geen gegevensbestand gevonden. De agenda wordt automatisch bijgewerkt.'
)
html = html.replace(
    'Nog geen CSV gevonden. Klik op "UiT verversen".',
    'Nog geen gegevensbestand gevonden. De agenda wordt automatisch bijgewerkt.'
)

# 4) Genre Night achtergrond opnieuw afdwingen, zonder andere skins te vervangen.
genre_fix = '''
/* Genre Night background safeguard */
body[data-theme="genre"]{
  background:
    linear-gradient(180deg, rgba(3,3,4,.74), rgba(8,8,10,.90)),
    radial-gradient(circle at 82% 0, rgba(225,28,36,.18), transparent 32%),
    url("./web/genre-night-bg.png") center top / cover fixed no-repeat,
    linear-gradient(180deg,#030304,#0b0b0e) !important;
}
'''

if "Genre Night background safeguard" not in html:
    html = html.replace("</style>", genre_fix + "\n</style>", 1)

INDEX.write_text(html, encoding="utf-8")

print(f"Aangepast: {INDEX}")
print(f"Backup:    {backup}")
if GENRE_BG.exists():
    print(f"Genre-achtergrond gevonden: {GENRE_BG}")
else:
    print("WAARSCHUWING: web/genre-night-bg.png niet gevonden.")
    print("De CSS is hersteld, maar plaats het bestaande genre-night-bg.png bestand terug in web/.")
