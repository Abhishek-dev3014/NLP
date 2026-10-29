#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python || ! -d frontend/node_modules ]]; then
  echo "Install dependencies first; see README.md."
  exit 1
fi
(cd backend && ../.venv/bin/alembic upgrade head)
(cd backend && exec ../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000) &
api_pid=$!
trap 'kill "$api_pid" 2>/dev/null || true' EXIT INT TERM
npm --prefix frontend run dev
