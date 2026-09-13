#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
WEB = PROJECT / "web"
DOCS = PROJECT / "docs"
DATA = DOCS / "data"

STATIC_SHIM = r"""
<style id="github-pages-public-fixes">
  /* De publieke GitHub Pages-site kan zelf niet scrapen. */
  .public-refresh-hidden { display: none !important; }
</style>

<script id="github-pages-static-adapter">
(() => {
  const originalFetch = window.fetch.bind(window);

  function jsonResponse(payload, status = 200) {
    return Promise.resolve(new Response(JSON.stringify(payload), {
      status,
      headers: {"Content-Type": "application/json; charset=utf-8"}
    }));
  }

  function isRefreshControl(el) {
    if (!el) return false;
    const candidate = el.closest ? el.closest("button, a, [role='button']") : null;
    if (!candidate) return false;

    const text = (candidate.textContent || "").trim().toLowerCase();
    const title = (candidate.getAttribute("title") || "").toLowerCase();
    const aria = (candidate.getAttribute("aria-label") || "").toLowerCase();
    const idClass = ((candidate.id || "") + " " + (candidate.className || "")).toLowerCase();

    return (
      text.includes("ververs") ||
      text === "refresh" ||
      title.includes("ververs") ||
      aria.includes("ververs") ||
      idClass.includes("refresh")
    );
  }

  function hideRefreshControls(root = document) {
    const candidates = root.querySelectorAll
      ? root.querySelectorAll("button, a, [role='button']")
      : [];
    for (const el of candidates) {
      if (isRefreshControl(el)) {
        el.classList.add("public-refresh-hidden");
        el.setAttribute("aria-hidden", "true");
        el.setAttribute("tabindex", "-1");
      }
    }
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
      return jsonResponse({ok: true, mode: "github-pages", static: true});
    }

    if (path.endsWith("/api/refresh")) {
      /* Nooit een publieke scrape proberen. Behandel dit als een geslaagde no-op. */
      return jsonResponse({
        ok: true,
        static: true,
        skipped: true,
        message: "De publieke agenda wordt dagelijks automatisch bijgewerkt."
      }, 200);
    }

    return originalFetch(input, init);
  };

  /* Blokkeer een refresh-click ook als de knop later door JavaScript wordt opgebouwd. */
  document.addEventListener("click", (event) => {
    if (isRefreshControl(event.target)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      return false;
    }
  }, true);

  document.addEventListener("DOMContentLoaded", () => {
    hideRefreshControls();

    const observer = new MutationObserver(() => hideRefreshControls());
    observer.observe(document.documentElement, {
      childList: true,
      subtree: true
    });
  });
})();
</script>
"""

def inject_adapter(html: str) -> str:
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

    # Vervang een oudere adapter wanneer die al in docs/index.html zou zitten.
    marker = '<script id="github-pages-static-adapter">'
    if marker in html:
        # We bouwen sowieso vanaf web/index.html, dus dit is vooral extra veiligheid.
        pass

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

    docs_web = DOCS / "web"
    if docs_web.exists():
        shutil.rmtree(docs_web)
    shutil.copytree(WEB, docs_web)

    html = source_index.read_text(encoding="utf-8")
    (DOCS / "index.html").write_text(inject_adapter(html), encoding="utf-8")

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
