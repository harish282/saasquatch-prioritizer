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
scripts/   run.sh · seed.sh · reset.sh · e2e_check.sh
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

---

## Architecture & design decisions

| Decision | Choice | Why |
|---|---|---|
| Backend | **FastAPI** (Python) | Caprae's own live stack is Flask on Ubuntu nginx; their job posting names FastAPI/Flask. Python keeps the scoring/enrichment logic readable. |
| Storage | **SQLAlchemy + SQLite (`backend/instance/`)** | Zero-infra so the grader can run it anywhere; schema maps 1:1 to Postgres (swap `DATABASE_URL`). |
| Frontend | **React + Vite + Tailwind** | Matches Caprae's React/Next.js apps; same dark `#121826` design language. |
| Hosting (prod path) | Ubuntu + nginx (reverse-proxying uvicorn) + CloudFront | Mirrors `data.saasquatchleads.com` (nginx on EC2). |
| Scraping | **Pluggable source adapters** (`scraper.py`) | `business_directory_card`, `business_directory_table`, `public_registry`. Swapping CSS selectors adapts a *changed* site layout — the rubric's "changing websites" test. Runs offline on fixtures so the demo is deterministic and TOS-safe. |

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

## 2-minute demo script (record this with the app on screen)

1. **0:00 – Hook (10s)** — "SaaSquatch finds leads but doesn't tell you *who to call
   first*. I fixed that in 5 hours: every lead now gets an ICP, completeness and
   confidence score, plus dedup and email validation."
2. **0:15 – Show the queue (25s)** — "37 leads, tiered hot/warm/cold. Sortable by
   priority. BerryClean at 92 — perfect fit: US cleaning service, 59 staff, verified
   email."
3. **0:40 – Explain the score drawer (25s)** — Open a lead. "Why 92? ICP 98 — right
   industry/location/size; confidence 75 — email MX-verified; freshness from the
   capture date. Compare with Northwind: great fit but *no contact info* — the
   outreachability gate drops it to warm, not hot."
4. **1:05 – Dedup tab (20s)** — "Two BerryClean records from different sources,
   99% match. The engine keeps the richer one; one click resolves the duplicate."
5. **1:25 – Validation + export (15s)** — "Invalid/disposable emails are auto-flagged
   (Redwood Pest Control's fake domain). Export CSV honours every filter — straight
   into your outreach tool."
6. **1:40 – Close (20s)** — "Three decisions I'd defend: Python backend because it
   matches your stack and keeps scoring readable; the market gate because fit beats
   polish; offline fixtures so scraping is ethical and deterministic."

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
```