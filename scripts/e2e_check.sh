#!/usr/bin/env bash
# Self-contained end-to-end check: starts backend + frontend, proxies a request,
# then tears everything down.
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"

(cd "$ROOT/backend" && exec "$ROOT/.venv/bin/uvicorn" app.main:app \
  --host 127.0.0.1 --port 8000 >/tmp/opencode/e2e_backend.log 2>&1) &
BACK_PID=$!

(cd "$ROOT/frontend" && npm run dev -- --port 5173 --strictPort \
  >/tmp/opencode/e2e_vite.log 2>&1 &)
VITE_PID=$!

cleanup() {
  kill "$BACK_PID" 2>/dev/null
  pkill -f "[v]ite --port 5173" 2>/dev/null
}
trap cleanup EXIT

sleep 6

echo "== backend health =="
curl -s -m 4 http://127.0.0.1:8000/api/health; echo
echo "== via vite proxy /api/leads =="
curl -s -m 4 "http://127.0.0.1:5173/api/leads?per_page=2&sort=priority_score&order=desc" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('total', d['total']); [print(' -', l['priority_score'], l['tier'], l['company']) for l in d['leads']]"
echo "== vite serves index =="
curl -s -m 4 http://127.0.0.1:5173/ | grep -o '<title>[^<]*</title>'
echo "== export csv =="
curl -s -m 4 "http://127.0.0.1:5173/api/export.csv?tier=hot" | head -2
echo "== done =="