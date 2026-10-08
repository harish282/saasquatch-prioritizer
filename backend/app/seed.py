"""Seed and ingest pipeline: loads seed dataset + scrapes fixtures, then scores
and de-duplicates everything. Safe to run repeatedly (idempotent per record)."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .config import SEED_FILE
from .dedup import group_duplicates
from .models import Lead
from .scoring import score_lead
from .scraper import RawLead, _normalize_country, run_fixture

log = logging.getLogger("seed")
_CAPTURE_ATTRS = ("owner_first_name", "owner_last_name", "owner_email", "owner_phone")


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def upsert_from_json(db: Session, row: dict) -> int:
    """Insert a lead from the seed dataset (idempotent on company+email)."""
    company = row.get("company", "")
    email = row.get("owner_email")
    existing = None
    if email:
        existing = db.query(Lead).filter(Lead.owner_email == email).first()
    if existing is None:
        lead = Lead(
            company=company,
            domain=str(row.get("domain") or row.get("website") or "").strip() or None,
            website=row.get("website"),
            industry=row.get("industry"),
            city=row.get("city"),
            country=_normalize_country(row.get("country")) or row.get("country"),
            employees=row.get("employees"),
            revenue_estimate_usd=row.get("revenue_estimate_usd"),
            owner_first_name=row.get("owner_first_name"),
            owner_last_name=row.get("owner_last_name"),
            owner_email=email,
            owner_phone=row.get("owner_phone"),
            company_phone=row.get("company_phone"),
            company_linkedin=row.get("company_linkedin"),
            description=row.get("description"),
            sources=row.get("sources") or [],
        )
        captured = _parse_ts((row.get("sources") or [{}])[0].get("captured_at"))
        lead.captured_at = captured or datetime.now(timezone.utc)
        db.add(lead)
    return 1 if existing is None else 0


def ingest_raw(db: Session, raw: RawLead, source_name: str, captured_at: datetime | None = None) -> Lead | None:
    if raw.skip:
        return None
    lead = Lead(
        company=raw.company,
        domain=raw.domain,
        website=raw.website,
        industry=raw.industry,
        city=raw.city,
        country=raw.country,
        employees=raw.employees,
        owner_first_name=raw.owner_first_name,
        owner_last_name=raw.owner_last_name,
        owner_email=raw.owner_email,
        owner_phone=raw.owner_phone,
        company_phone=raw.company_phone,
        company_linkedin=raw.company_linkedin,
        description=raw.description,
        sources=[{"source": source_name, "url": raw.source_url,
                  "captured_at": (captured_at or datetime.now(timezone.utc)).isoformat()}],
        captured_at=captured_at or datetime.now(timezone.utc),
    )
    db.add(lead)
    return lead


def seed(db: Session, include_fixtures: bool = True) -> dict:
    stats = {"seeded": 0, "scraped": 0, "skipped": 0, "scored": 0, "dedup_groups": 0}

    if SEED_FILE.exists():
        data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
        for row in data:
            stats["seeded"] += upsert_from_json(db, row)

    if include_fixtures:
        for source_name, raws in run_fixture():
            for raw in raws:
                if raw.skip:
                    stats["skipped"] += 1
                    continue
                lead = ingest_raw(db, raw, source_name)
                stats["scraped"] += 1 if lead else 0

    db.commit()

    leads = db.query(Lead).all()
    for lead in leads:
        score_lead(lead)
    db.commit()
    stats["scored"] = len(leads)

    report = group_duplicates(db)
    stats["dedup_groups"] = len(report)
    log.info("Seeded %s leads, %s dedup groups", len(leads), len(report))
    return stats