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

noir_css = r'''
/* Cinema Noir typography refinement */
body[data-theme="noir"] .title h1{
  font-family:"Didot","Bodoni 72","Bodoni MT","Times New Roman",serif;
  font-size:50px;
  font-weight:400;
  letter-spacing:.14em;
  text-transform:uppercase;
  line-height:.95;
  white-space:nowrap;
  text-shadow:0 2px 0 rgba(0,0,0,.72), 0 0 18px rgba(255,255,255,.05);
}

body[data-theme="noir"] .kicker{
  font-family:"Didot","Bodoni 72","Bodoni MT","Times New Roman",serif;
  font-size:11px;
  font-weight:400;
  letter-spacing:.30em;
  text-transform:uppercase;
}

body[data-theme="noir"] .name{
  font-family:"Didot","Bodoni 72","Bodoni MT","Times New Roman",serif;
  font-size:21px;
  font-weight:500;
  letter-spacing:.035em;
  line-height:1.18;
}

body[data-theme="noir"] .hero-card{
  background:
    linear-gradient(135deg, rgba(255,255,255,.035), transparent 38%),
    linear-gradient(180deg, rgba(12,12,16,.98), rgba(20,20,25,.97));
}

@media(max-width:900px){
  body[data-theme="noir"] .title h1{
    font-size:38px;
    letter-spacing:.09em;
    white-space:normal;
  }
}
'''

if "Cinema Noir typography refinement" not in html:
    html = html.replace("</style>", noir_css + "\n</style>", 1)

pattern = re.compile(
    r"""if\(chosen==='uitbrugge'\)\{.*?\n\s*\}\s*else if\(chosen==='razorreel'\)\{.*?\n\s*\}(?:\s*else if\(chosen==='arthouse'\)\{.*?\n\s*\})?\s*else\{.*?\n\s*\}""",
    re.DOTALL
)

replacement = """if(chosen==='uitbrugge'){
   title.textContent='FILMAGENDA';
   subtitle.textContent='Filmvertoningen, specials, festivals en audiovisuele activiteiten in Brugge.';
 }else if(chosen==='razorreel'){
   title.textContent='RAZOR REEL';
   subtitle.textContent='FLANDERS FILM FEST · BRUGGE FILMAGENDA';
 }else if(chosen==='arthouse'){
   title.textContent='BRUGGE FILM AGENDA';
   subtitle.textContent='Een sobere, festivalachtige blik op film en audiovisuele events in Brugge.';
 }else if(chosen==='noir' || chosen==='retro70' || chosen==='genre'){
   title.textContent='BRUGGE FILM AGENDA';
   subtitle.textContent='Een cinematische bladerlaag boven UiTinVlaanderen voor Brugge — film, filmfestivals en aanverwante audiovisuele events in de komende 120 dagen.';
 }else{
   title.textContent='Brugge Film Tool';
   subtitle.textContent='Een cinematische bladerlaag boven UiTinVlaanderen voor Brugge — film, filmfestivals en aanverwante audiovisuele events in de komende 120 dagen.';
 }"""

new_html, n = pattern.subn(replacement, html, count=1)
if n != 1:
    raise SystemExit("Kon het titelblok in applyTheme() niet veilig vinden. Geen wijzigingen uitgevoerd.")

INDEX.write_text(new_html, encoding="utf-8")

print(f"Aangepast: {INDEX}")
print(f"Backup:    {backup}")
print("Titels aangepast voor Cinema Noir, Retro 70s en Genre Night.")
print("Cinema Noir typografie verfijnd.")
