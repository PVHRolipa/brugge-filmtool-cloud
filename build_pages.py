#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
WEB = PROJECT / "web"
DOCS = PROJECT / "docs"
DATA = DOCS / "data"
EVENTS_JSON = DATA / "events.json"

STATIC_SHIM = r"""
<script id="github-pages-static-adapter">
(() => {
  const originalFetch = window.fetch.bind(window);

  function jsonResponse(payload, status = 200) {
    return Promise.resolve(new Response(JSON.stringify(payload), {
      status,
      headers: {"Content-Type": "application/json; charset=utf-8"}
    }));
  }

  window.fetch = function(input, init) {
    const raw = typeof input === "string" ? input : (input && input.url) || "";
    let path = raw;
    try {
      path = new URL(raw, window.location.href).pathname;
    } catch (_) {}

    if (path.endsWith("/api/events")) {
      return originalFetch("./data/events.json?v=" + Date.now(), {
        cache: "no-store"
      });
    }

    if (path.endsWith("/api/health")) {
      return jsonResponse({
        ok: true,
        mode: "github-pages",
        static: true
      });
    }

    if (path.endsWith("/api/refresh")) {
      return jsonResponse({
        ok: false,
        static: true,
        message: "De publieke Filmtool wordt dagelijks automatisch om 12:00 bijgewerkt."
      }, 409);
    }

    return originalFetch(input, init);
  };

  document.addEventListener("DOMContentLoaded", () => {
    for (const button of document.querySelectorAll("button")) {
      const text = (button.textContent || "").trim().toLowerCase();
      if (text === "verversen" || text === "refresh" || text.includes("ververs data")) {
        button.disabled = true;
        button.title = "De publieke Filmtool wordt dagelijks automatisch om 12:00 bijgewerkt.";
      }
    }
  });
})();
</script>
"""

def inject_adapter(html: str) -> str:
    # GitHub Pages for a project lives below /brugge-filmtool-cloud/.
    # Convert the few root-relative local-server asset paths to project-relative paths.
    replacements = {
        'href="/manifest.webmanifest"': 'href="./manifest.webmanifest"',
        "href='/manifest.webmanifest'": "href='./manifest.webmanifest'",
        'href="/apple-touch-icon.png"': 'href="./apple-touch-icon.png"',
        "href='/apple-touch-icon.png'": "href='./apple-touch-icon.png'",
        'href="/icon-192.png"': 'href="./icon-192.png"',
        "href='/icon-192.png'": "href='./icon-192.png'",
        'href="/icon-512.png"': 'href="./icon-512.png"',
        "href='/icon-512.png'": "href='./icon-512.png'",
        'src="/web/': 'src="./web/',
        "src='/web/": "src='./web/",
        'href="/web/': 'href="./web/',
        "href='/web/": "href='./web/",
        'url("/web/': 'url("./web/',
        "url('/web/": "url('./web/",
    }
    for old, new in replacements.items():
        html = html.replace(old, new)

    if "github-pages-static-adapter" not in html:
        if "<head>" in html:
            html = html.replace("<head>", "<head>\n" + STATIC_SHIM, 1)
        elif "</head>" in html:
            html = html.replace("</head>", STATIC_SHIM + "\n</head>", 1)
        else:
            html = STATIC_SHIM + "\n" + html
    return html

def copy_if_exists(src: Path, dst: Path) -> None:
    if src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

def main() -> None:
    source_index = WEB / "index.html"
    if not source_index.exists():
        raise SystemExit(f"Niet gevonden: {source_index}")

    DOCS.mkdir(exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)

    # Keep all existing skins/assets intact.
    docs_web = DOCS / "web"
    if docs_web.exists():
        shutil.rmtree(docs_web)
    shutil.copytree(WEB, docs_web)

    html = source_index.read_text(encoding="utf-8")
    (DOCS / "index.html").write_text(inject_adapter(html), encoding="utf-8")

    # Copy root PWA assets used by the local server, when present.
    for name in ("manifest.webmanifest", "apple-touch-icon.png", "icon-192.png", "icon-512.png"):
        copy_if_exists(PROJECT / name, DOCS / name)

    (DOCS / ".nojekyll").write_text("", encoding="utf-8")

    meta = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "local Brugge Filmtool scraper",
    }
    (DATA / "update.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"GitHub Pages site opgebouwd in: {DOCS}")

if __name__ == "__main__":
    main()
