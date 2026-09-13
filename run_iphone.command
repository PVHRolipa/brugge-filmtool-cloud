#!/bin/bash
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Eerste start: Python-omgeving wordt aangemaakt..."
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install -q -r requirements.txt
export BRUGGE_FILM_HOST=0.0.0.0
python browser.py
