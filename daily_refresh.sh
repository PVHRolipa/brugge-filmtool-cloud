#!/bin/zsh
set -euo pipefail

PROJECT="$HOME/Desktop/brugge-filmtool-cloud"
LOG_DIR="$PROJECT/logs"
LOG_FILE="$LOG_DIR/daily_refresh.log"
PORT="8765"

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
  curl -fsS -X POST "http://127.0.0.1:${PORT}/api/refresh"
  echo ""
  echo "Refresh voltooid."

  echo "Publieke JSON exporteren..."
  mkdir -p "$PROJECT/docs/data"
  TMP_EVENTS="$PROJECT/docs/data/events.json.tmp"

  curl -fsS "http://127.0.0.1:${PORT}/api/events" > "$TMP_EVENTS"

  # Controleer dat de export geldige JSON is voor we de vorige publieke data vervangen.
  python3 - "$TMP_EVENTS" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
with p.open("r", encoding="utf-8") as f:
    data = json.load(f)
if data is None:
    raise SystemExit("Lege JSON-export")
print("JSON-export geldig.")
PY

  mv "$TMP_EVENTS" "$PROJECT/docs/data/events.json"

  cleanup
  trap - EXIT

  echo "GitHub Pages-versie bouwen..."
  python3 "$PROJECT/build_pages.py"

  # Alleen de data en de gebouwde publieke site publiceren.
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
