#!/bin/zsh
set -euo pipefail

PROJECT="$HOME/Desktop/brugge-filmtool-cloud"
LOG_DIR="$PROJECT/logs"
LOG_FILE="$LOG_DIR/daily_refresh.log"
PORT="8765"

# Maximaal 5 minuten wachten tot de lokale agenda effectief gevuld is.
MAX_WAIT_SECONDS=300
POLL_SECONDS=5

mkdir -p "$LOG_DIR"
cd "$PROJECT"

{
  echo ""
  echo "============================================================"
  echo "Brugge Filmtool update: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "============================================================"

  if [ -f "$PROJECT/.venv/bin/activate" ]; then
    source "$PROJECT/.venv/bin/activate"
  elif [ -f "$PROJECT/venv/bin/activate" ]; then
    source "$PROJECT/venv/bin/activate"
  fi

  export BRUGGE_FILM_HOST="127.0.0.1"
  export BRUGGE_FILM_PORT="$PORT"

  python3 browser.py > "$LOG_DIR/browser_refresh.log" 2>&1 &
  SERVER_PID=$!

  cleanup() {
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  }
  trap cleanup EXIT

  SERVER_READY=0
  for i in {1..30}; do
    if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
      SERVER_READY=1
      break
    fi
    sleep 1
  done

  if [ "$SERVER_READY" -ne 1 ]; then
    echo "FOUT: lokale Filmtool-server startte niet."
    exit 1
  fi

  echo "UiT-data lokaal verversen..."
  # De refresh kan de opbouw starten en terugkeren vóór /api/events al gevuld is.
  curl -fsS -X POST "http://127.0.0.1:${PORT}/api/refresh" || true
  echo ""
  echo "Refresh gestart. Wachten tot de agenda effectief gevuld is..."

  TMP_CHECK="$LOG_DIR/events_check.json"
  ELAPSED=0
  EVENT_COUNT=0

  while [ "$ELAPSED" -lt "$MAX_WAIT_SECONDS" ]; do
    if curl -fsS "http://127.0.0.1:${PORT}/api/events" > "$TMP_CHECK" 2>/dev/null; then
      EVENT_COUNT=$(
        python3 - "$TMP_CHECK" <<'PY'
import json, sys
from pathlib import Path

p = Path(sys.argv[1])
try:
    data = json.loads(p.read_text(encoding="utf-8"))
except Exception:
    print(0)
    raise SystemExit

if isinstance(data, dict):
    events = data.get("events")
    print(len(events) if isinstance(events, list) else 0)
elif isinstance(data, list):
    print(len(data))
else:
    print(0)
PY
      )

      if [ "${EVENT_COUNT:-0}" -gt 0 ]; then
        echo "Agenda klaar: $EVENT_COUNT events gevonden."
        break
      fi
    fi

    sleep "$POLL_SECONDS"
    ELAPSED=$((ELAPSED + POLL_SECONDS))
    echo "Nog aan het opbouwen... ${ELAPSED}s"
  done

  if [ "${EVENT_COUNT:-0}" -le 0 ]; then
    echo "FOUT: na ${MAX_WAIT_SECONDS}s nog geen events. Publieke data wordt NIET overschreven."
    exit 1
  fi

  echo "Publieke JSON exporteren..."
  mkdir -p "$PROJECT/docs/data"
  TMP_EVENTS="$PROJECT/docs/data/events.json.tmp"

  curl -fsS "http://127.0.0.1:${PORT}/api/events" > "$TMP_EVENTS"

  # Finale veiligheidscontrole: alleen vervangen bij geldige JSON met minstens 1 event.
  FINAL_COUNT=$(
    python3 - "$TMP_EVENTS" <<'PY'
import json, sys
from pathlib import Path

p = Path(sys.argv[1])
data = json.loads(p.read_text(encoding="utf-8"))

if isinstance(data, dict):
    events = data.get("events")
    count = len(events) if isinstance(events, list) else 0
elif isinstance(data, list):
    count = len(data)
else:
    count = 0

if count <= 0:
    raise SystemExit("Export bevat 0 events; bestaande publieke data blijft behouden.")

print(count)
PY
  )

  mv "$TMP_EVENTS" "$PROJECT/docs/data/events.json"
  echo "Publieke export klaar: $FINAL_COUNT events."

  cleanup
  trap - EXIT

  echo "GitHub Pages-versie bouwen..."
  python3 "$PROJECT/build_pages.py"

  git add data/ docs/ build_pages.py daily_refresh.sh .gitignore 2>/dev/null || true

  if git diff --cached --quiet; then
    echo "Geen wijzigingen om te publiceren."
  else
    git commit -m "Daily film update $(date '+%Y-%m-%d %H:%M')"
    git push origin main
    echo "Nieuwe Filmtool-data en GitHub Pages-site gepusht."
  fi

  echo "Klaar: $(date '+%Y-%m-%d %H:%M:%S')"
} >> "$LOG_FILE" 2>&1
