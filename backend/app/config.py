"""Central configuration for the SaaSquatch Prioritizer."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'saasquatch.db'}")
SEED_FILE = DATA_DIR / "seed_leads.json"
FIXTURES_DIR = DATA_DIR / "fixtures"

CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

# Target market profile used by the ICP scorer. Modelling the searcher/ETA buyer:
# US-founded small-to-medium service businesses with real web presence.
ICP = {
    "country_weight": 0.25,
    "preferred_countries": ["USA", "US", "Canada", "GB", "United Kingdom", "UK"],
    "industry_weight": 0.3,
    "preferred_industries": [
        "house cleaning service",
        "landscaping",
        "home services",
        "auto repair",
        "roofing",
        "plumbing",
        "electrical",
        "HVAC",
        "dental",
        "salon",
        "spa",
        "fitness",
        "accounting",
        "consulting",
        "marketing",
        "logistics",
        "manufacturing",
        "software",
        "IT services",
        "construction",
        "restaurant",
        "café",
        "retail",
    ],
    "size_weight": 0.25,
    "ideal_employee_min": 3,
    "ideal_employee_max": 500,
    "web_weight": 0.1,
    "revenue_weight": 0.1,
    "revenue_floor_usd": 250_000,
    "revenue_ideal_usd": 2_000_000,
}

# Weights for the composite priority score (sum = 1.0)
PRIORITY_WEIGHTS = {
    "icp": 0.4,
    "completeness": 0.2,
    "confidence": 0.3,
    "freshness": 0.1,
}

INSTANCE_DIR.mkdir(parents=True, exist_ok=True)