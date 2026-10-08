#!/usr/bin/env bash
# Reset the database entirely and reseed from scratch.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
rm -f instance/saasquatch.db
"$ROOT/.venv/bin/python" -c "
from app.database import init_db, SessionLocal
init_db()
from app import seed
db = SessionLocal()
try:
    stats = seed.seed(db)
    print('Reseeded:', stats)
finally:
    db.close()
"