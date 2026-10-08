#!/usr/bin/env bash
# Run the unit test suite (isolated temp DB, no network required).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
"$ROOT/.venv/bin/python" -m pytest backend/tests "$@"