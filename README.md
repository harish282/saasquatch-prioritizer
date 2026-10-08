# SaaSquatch Prioritizer

A 5-hour AI-Readiness build for the **Full Stack Developer** challenge at Caprae Capital.

**One-line pitch:** *SaaSquatch tells you who to call first* — a lead-intelligence layer
that scrapes public sources, then **prioritizes, de-duplicates, and validates** every
lead so a sales team never wastes outreach on a bad record.

Analysed the live product (`saasquatchleads.com`) and found the highest-leverage gap:
leads were collected but **not ranked** — the "AI Company Scoring" value proposition
was advertised but never surfaced to the user, there was no dedup, and no per-field
quality confidence. This build ships exactly that gap as a product-grade feature.

```
frontend/  React + Vite + Tailwind (dark dashboard, same aesthetic as the real app)
backend/   FastAPI + SQLAlchemy + SQLite  ->  nginx/Ubuntu (the stack Caprae uses)
data/      seed dataset + scraping fixtures (real HTML/JSON the pipeline parses)
scripts/   run.sh · seed.sh · reset.sh · test.sh · e2e_check.sh
```

---

## Quick start

```bash
# 1. Backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
scripts/reset.sh                 # build DB + seed demo data
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend

# 2. Frontend
cd frontend && npm install && npm run dev   # -> http://localhost:5173

# or just:
scripts/run.sh                   # starts both, tails logs
```

Open **http://localhost:5173**. The first load auto-seeds 37 leads (22 curated + 15
parsed from 3 scraping fixtures) and computes every score.

## Testing

**Unit tests** (`scripts/test.sh`, ~51 tests): scoring engines (market gate,
outreachability gate, tiers), dedup (compound-suffix domains, fuzzy names, resolve),
field validation (email syntax/MX, phone shapes, domain), and a full API smoke suite
(health, stats, filters, dedup report, CSV export, fixture re-scrape). Tests run
against an isolated temp DB with DNS disabled — deterministic, offline, fast:

```bash
scripts/test.sh            # pytest backend/tests
```

**E2E check** (`scripts/e2e_check.sh`): boots backend + frontend, verifies health,
the Vite `/api` proxy, sorted lead queue, and CSV export through the real stack, then
tears everything down.

---

## Architecture & design decisions

| Decision | Choice | Why |
|---|---|---|
| Backend | **FastAPI** (Python) | Caprae's own live stack is Flask on Ubuntu nginx; their job posting names FastAPI/Flask. Python keeps the scoring/enrichment logic readable. |
| Storage | **SQLAlchemy + SQLite (`backend/instance/`)** | Zero-infra so it runs anywhere out of the box; schema maps 1:1 to Postgres (swap `DATABASE_URL`). |
| Frontend | **React + Vite + Tailwind** | Matches Caprae's React/Next.js apps; same dark `#121826` design language. |
| Hosting (prod path) | Ubuntu + nginx (reverse-proxying uvicorn) + CloudFront | Mirrors `data.saasquatchleads.com` (nginx on EC2). |
| Scraping | **Pluggable source adapters** (`scraper.py`) | `business_directory_card`, `business_directory_table`, `public_registry`. Swapping CSS selectors adapts to a *changed* site layout. Runs offline on fixtures so the demo is deterministic and TOS-safe. |

**Scoring model** (`scoring.py`) — three explainable sub-scores + a gate:

- **ICP fit (40%)** — country / industry / size / web-presence / revenue, weighted
  toward the searcher profile: US+CA+UK SMB service businesses, 3–500 employees,
  \$250k–\$2M revenue.
- **Completeness (20%)** — share of 8 high-value fields populated.
- **Confidence (30%)** — email syntax + **real MX lookup** (dnspython), disposable-domain
  rejection, phone E.164 shape, multi-source corroboration.
- **Freshness (10%)** — recency decay of the source capture.
- **Market gate** — a record outside the ICP can *never* rank hot (or warm if truly
  out-of-market). A 12,000-employee German manufacturer with perfect data scores
  cold. That is the point: **fit beats polish.**

**Dedup** (`dedup.py`) — registry-suffix-aware domain normalisation (`acme.co.uk`
→ `acme`) + fuzzy company-name token match. Each cluster keeps the richest record
as primary; "resolve" in the UI removes duplicates.

**Validation** (`validation.py`) — every network check is defensive: if DNS is down,
a field degrades to `unknown` rather than crashing the scorer.

---

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/stats` | Dashboard aggregates |
| `GET /api/leads` | Filterable/sortable lead queue (`q, country, industry, tier, min_score, has_email, sort, order`) |
| `GET /api/leads/{id}` | Full lead + score breakdown |
| `GET /api/report/dedup` | Duplicate clusters |
| `POST /api/scrape` | Re-parse the 3 fixture sources (re-scrapes also demonstrate dedup) |
| `GET /api/export.csv` | CSV export honouring the same filters (one-click in UI) |

Interactive docs at `/docs` when the backend runs.

---

## What I'd build with more time

- Live multi-source ingestion (adapter interface is ready; `mode='url'` is disabled
  deliberately in the demo to keep scraping safe/TOS-compliant).
- CRM sync (HubSpot import/export) — the export is already CSV-shaped for it.
- LLM-written email drafts keyed to the priority tier.

## Scope guards

- No auth/payments — picked business logic over plumbing in 5 hours.
- Scraping runs against bundled public fixtures, not live third-party sites, for
  deterministic grading + ethical data collection.
- LinkedIn is surfaced as a *link* only (no scraping) — respects their TOS.

---

## Files

```
backend/app/
  main.py         FastAPI routes
  scoring.py      ICP + completeness + confidence + freshness + market gate
  validation.py   email/MX, phone, domain checks (network-safe)
  dedup.py        domain + fuzzy-name dedup
  scraper.py      multi-source adapters (HTML card/table, JSON registry)
  seed.py         idempotent seeding + ingest pipeline
  models.py       lead schema
data/
  seed_leads.json         22 curated records (incl. edge cases)
  fixtures/*.html|json    3 scrape sources the pipeline genuinely parses
frontend/src/
  App.jsx                  tabs, filters, state
  components/              header, stats, lead table, score drawer, dedup, export
backend/tests/
  conftest.py              isolated temp DB + offline-network setup
  test_scoring.py          market gate, outreachability, tiers
  test_dedup.py            domain normalisation + cluster marking
  test_validation.py       email / phone / domain checks
  test_api.py              health, queue, dedup report, resolve, CSV, scrape
```