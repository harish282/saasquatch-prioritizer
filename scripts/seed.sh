#!/usr/bin/env bash
# Seed the database (idempotent) without starting the server.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"
"$ROOT/.venv/bin/python" -c "
from app.database import init_db, SessionLocal
init_db()
from app import seed
from app.models import Lead
db = SessionLocal()
try:
    if db.query(Lead).count() == 0:
        stats = seed.seed(db)
        print('Seeded:', stats)
    else:
        print(f'DB already has {db.query(Lead).count()} leads — leaving untouched.')
finally:
    db.close()
"