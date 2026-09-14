#!/usr/bin/env python3
from pathlib import Path
import re
import shutil
from datetime import datetime

PROJECT = Path(__file__).resolve().parent
INDEX = PROJECT / "web" / "index.html"

if not INDEX.exists():
    raise SystemExit(f"Niet gevonden: {INDEX}")

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup = INDEX.with_name(f"index.backup-{stamp}.html")
shutil.copy2(INDEX, backup)

html = INDEX.read_text(encoding="utf-8")

arthouse_css = """
/* Arthouse typography refinement */
body[data-theme="arthouse"] .title h1{
  font-family:"Arial Narrow","Helvetica Neue Condensed","Avenir Next Condensed","Helvetica Neue",Arial,sans-serif;
  font-size:54px;
  font-weight:500;
  letter-spacing:.16em;
  text-transform:uppercase;
  line-height:.95;
  white-space:nowrap;
}

body[data-theme="arthouse"] .kicker{
  font-family:"Arial Narrow","Helvetica Neue Condensed","Avenir Next Condensed","Helvetica Neue",Arial,sans-serif;
  letter-spacing:.28em;
  text-transform:uppercase;
  font-size:11px;
  font-weight:500;
}

body[data-theme="arthouse"] .name{
  font-family:"Arial Narrow","Helvetica Neue Condensed","Avenir Next Condensed","Helvetica Neue",Arial,sans-serif;
  font-size:22px;
  font-weight:600;
  letter-spacing:.045em;
  line-height:1.15;
}

body[data-theme="arthouse"] .venue,
body[data-theme="arthouse"] .desc,
body[data-theme="arthouse"] .status{
  letter-spacing:.015em;
}

@media(max-width:900px){
  body[data-theme="arthouse"] .title h1{
    font-size:40px;
    letter-spacing:.10em;
    white-space:normal;
  }
}
"""

if "Arthouse typography refinement" not in html:
    html = html.replace("</style>", arthouse_css + "\n</style>", 1)

old = """if(chosen==='uitbrugge'){
   title.textContent='FILMAGENDA';
   subtitle.textContent='Filmvertoningen, specials, festivals en audiovisuele activiteiten in Brugge.';
 }else if(chosen==='razorreel'){
   title.textContent='RAZOR REEL';
   subtitle.textContent='FLANDERS FILM FEST · BRUGGE FILMAGENDA';
 }else{
   title.textContent='Brugge Film Tool';
   subtitle.textContent='Een cinematische bladerlaag boven UiTinVlaanderen voor Brugge — film, filmfestivals en aanverwante audiovisuele events in de komende 120 dagen.';
 }"""

new = """if(chosen==='uitbrugge'){
   title.textContent='FILMAGENDA';
   subtitle.textContent='Filmvertoningen, specials, festivals en audiovisuele activiteiten in Brugge.';
 }else if(chosen==='razorreel'){
   title.textContent='RAZOR REEL';
   subtitle.textContent='FLANDERS FILM FEST · BRUGGE FILMAGENDA';
 }else if(chosen==='arthouse'){
   title.textContent='BRUGGE FILM AGENDA';
   subtitle.textContent='Een sobere, festivalachtige blik op film en audiovisuele events in Brugge.';
 }else{
   title.textContent='Brugge Film Tool';
   subtitle.textContent='Een cinematische bladerlaag boven UiTinVlaanderen voor Brugge — film, filmfestivals en aanverwante audiovisuele events in de komende 120 dagen.';
 }"""

if old not in html:
    raise SystemExit("Kon het theme-blok niet veilig vinden. Geen wijziging uitgevoerd.")

html = html.replace(old, new, 1)

INDEX.write_text(html, encoding="utf-8")

print(f"Aangepast: {INDEX}")
print(f"Backup:    {backup}")
print("Arthouse titel: BRUGGE FILM AGENDA")
