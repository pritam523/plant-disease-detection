#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

PY=".venv-app/bin/python"
if [ ! -x "$PY" ] || ! "$PY" -c "import sys" >/dev/null 2>&1; then
  echo "Creating local Python environment. This happens only once per PC."
  rm -rf .venv-app
  if ! python3.12 -m venv .venv-app; then
    rm -rf .venv-app
    python3 -m venv .venv-app
  fi
  PY=".venv-app/bin/python"
  "$PY" -m pip install --upgrade pip
  "$PY" -m pip install -r requirements.txt
fi

if [ ! -f .env ]; then
  echo "Creating .env from .env.example."
  echo "Add optional API keys and admin settings later; see CONFIGURATION.md."
  cp .env.example .env
fi

echo
echo "Starting Plant Disease Detection..."
echo "Open http://127.0.0.1:8000/ in your browser."
echo "Press Ctrl+C to stop the server."
echo

"$PY" run.py check
"$PY" run.py
