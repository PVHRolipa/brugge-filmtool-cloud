from __future__ import annotations

import csv
import json
import mimetypes
import os
import socket
import sys
import threading
import time
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import config
from csv_store import write_csv
from uit_scraper import scrape

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
CSV_PATH = BASE_DIR / config.OUTPUT_CSV

# Local mode keeps the old behaviour. Cloud hosts such as Render provide PORT;
# in that case bind publicly and use their assigned port.
CLOUD_PORT = os.environ.get("PORT")
HOST = os.environ.get("BRUGGE_FILM_HOST", "0.0.0.0" if CLOUD_PORT else "127.0.0.1")
PORT = int(CLOUD_PORT or os.environ.get("BRUGGE_FILM_PORT", "8765"))
REFRESH_COOLDOWN_SECONDS = int(os.environ.get("BRUGGE_FILM_REFRESH_COOLDOWN_SECONDS", "600"))
AUTO_REFRESH_HOURS = float(os.environ.get("BRUGGE_FILM_AUTO_REFRESH_HOURS", "6"))

_REFRESH_LOCK = threading.Lock()
_LAST_REFRESH_MONOTONIC = 0.0
_LAST_REFRESH_ERROR: str | None = None


def _lan_ip() -> str | None:
    """Best-effort local IPv4 address for opening the tool from a phone on the same Wi-Fi."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return None
    finally:
        sock.close()


def _load_events() -> list[dict[str, str]]:
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _csv_age_hours() -> float | None:
    if not CSV_PATH.exists():
        return None
    return max(0.0, (time.time() - CSV_PATH.stat().st_mtime) / 3600.0)


def _summary(events: list[dict[str, str]]) -> dict:
    categories: dict[str, int] = {}
    for row in events:
        category = row.get("Category", "").strip() or "Onbekend"
        categories[category] = categories.get(category, 0) + 1
    venues = sorted({row.get("Venue", "").strip() for row in events if row.get("Venue", "").strip()})
    image_count = sum(1 for row in events if row.get("Image URL", "").strip())
    return {
        "total": len(events),
        "image_count": image_count,
        "categories": categories,
        "venues": venues,
        "csv_exists": CSV_PATH.exists(),
        "csv_path": str(CSV_PATH),
        "updated_at": datetime.fromtimestamp(CSV_PATH.stat().st_mtime).isoformat(timespec="seconds") if CSV_PATH.exists() else None,
        "refreshing": _REFRESH_LOCK.locked(),
        "last_refresh_error": _LAST_REFRESH_ERROR,
    }


def _refresh_data(*, force: bool = False) -> tuple[bool, str | None]:
    """Refresh shared event data once.

    Returns (changed, message). A non-forced public refresh is skipped during
    the cooldown. Only one scrape can run at a time across all visitors.
    """
    global _LAST_REFRESH_MONOTONIC, _LAST_REFRESH_ERROR

    if not force and CSV_PATH.exists() and _LAST_REFRESH_MONOTONIC:
        remaining = REFRESH_COOLDOWN_SECONDS - (time.monotonic() - _LAST_REFRESH_MONOTONIC)
        if remaining > 0:
            return False, f"De agenda werd net ververst. Probeer opnieuw over {max(1, int(remaining // 60) + 1)} min."

    if not _REFRESH_LOCK.acquire(blocking=False):
        return False, "Een andere bezoeker is de agenda al aan het verversen."

    try:
        events = scrape()
        CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        write_csv(CSV_PATH, events)
        _LAST_REFRESH_MONOTONIC = time.monotonic()
        _LAST_REFRESH_ERROR = None
        return True, None
    except Exception as exc:  # noqa: BLE001
        _LAST_REFRESH_ERROR = str(exc)
        raise
    finally:
        _REFRESH_LOCK.release()


def _bootstrap_if_needed() -> None:
    age = _csv_age_hours()
    if age is None or age >= AUTO_REFRESH_HOURS:
        try:
            _refresh_data(force=True)
        except Exception as exc:  # noqa: BLE001
            print(f"Automatische UiT-refresh mislukt: {exc}")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send_json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path, content_type: str) -> None:
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path.startswith("/web/"):
            rel = path.removeprefix("/web/")
            target = (WEB_DIR / rel).resolve()
            if WEB_DIR.resolve() not in target.parents and target != WEB_DIR.resolve():
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in {"application/manifest+json", "application/javascript", "application/json"}:
                ctype += "; charset=utf-8"
            self._send_file(target, ctype)
            return
        if path == "/manifest.webmanifest":
            self._send_file(WEB_DIR / "manifest.webmanifest", "application/manifest+json; charset=utf-8")
            return
        if path in ("/apple-touch-icon.png", "/icon-192.png", "/icon-512.png"):
            self._send_file(WEB_DIR / path.lstrip("/"), "image/png")
            return
        if path == "/api/events":
            events = _load_events()
            self._send_json({"events": events, "summary": _summary(events)})
            return
        if path == "/api/health":
            self._send_json({"ok": True, "refreshing": _REFRESH_LOCK.locked()})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/refresh":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            changed, message = _refresh_data(force=False)
            rows = _load_events()
            self._send_json({
                "ok": True,
                "changed": changed,
                "message": message,
                "events": rows,
                "summary": _summary(rows),
            })
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> int:
    if not (WEB_DIR / "index.html").exists():
        print("Webinterface ontbreekt: web/index.html")
        return 1

    # On a cloud restart the local filesystem can be empty. Rebuild data in the
    # background so the public URL becomes useful without an administrator.
    threading.Thread(target=_bootstrap_if_needed, daemon=True, name="uit-bootstrap").start()

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    mac_url = f"http://127.0.0.1:{PORT}"
    lan_ip = _lan_ip()
    print("Brugge Film Tool — browser")
    if CLOUD_PORT:
        print(f"Cloud mode: 0.0.0.0:{PORT}")
    else:
        print(f"Mac:    {mac_url}")
        if HOST == "0.0.0.0":
            if lan_ip and not lan_ip.startswith("127."):
                print(f"iPhone: http://{lan_ip}:{PORT}  (zelfde wifi-netwerk)")
                print("Open dit iPhone-adres in Safari en kies Deel → Zet op beginscherm.")
            else:
                print("iPhone-adres kon niet automatisch worden bepaald.")
        print("Stoppen: Ctrl+C")
        threading.Timer(0.6, lambda: webbrowser.open(mac_url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBrowser gestopt.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
