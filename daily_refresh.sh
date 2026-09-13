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
  echo "Brugge Filmtool dagelijkse update: $(date '+%Y-%m-%d %H:%M:%S')"
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

  for i in {1..20}; do
    if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done

  echo "UiT-data verversen..."
  curl -fsS -X POST "http://127.0.0.1:${PORT}/api/refresh"
  echo ""
  echo "Refresh voltooid."

  cleanup
  trap - EXIT

  git add data/ web/ *.html *.json *.csv 2>/dev/null || true

  if git diff --cached --quiet; then
    echo "Geen wijzigingen om te publiceren."
  else
    git commit -m "Daily film update $(date '+%Y-%m-%d')"
    git push origin main
    echo "Nieuwe Filmtool-data naar GitHub gepusht."
  fi

  echo "Klaar: $(date '+%Y-%m-%d %H:%M:%S')"
} >> "$LOG_FILE" 2>&1
