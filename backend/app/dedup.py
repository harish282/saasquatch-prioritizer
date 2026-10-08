"""Deduplication.

Two passes:
  1. Domain normalisation (registry-aware suffix stripping, e.g. acme.co.uk -> acme)
  2. Fuzzy company-name match (token overlap) for records without a domain.

Leads in a group are ranked; the most complete/confident becomes primary and the
rest are flagged as duplicates (never silently deleted with the "keep primary" action).
"""

from __future__ import annotations

import re
import uuid

from sqlalchemy.orm import Session

from .models import Lead

_CLEAN = re.compile(r"[^a-z0-9]+")
_SUFFIXES = sorted({
    "com", "net", "org", "io", "co", "ai", "app", "dev", "edu", "gov", "info", "biz",
    "uk", "us", "ca", "au", "de", "fr", "nl", "se", "in", "jp", "cn", "br", "mx", "it",
    "es", "pl", "ru", "za", "nz", "sg", "hk", "no", "dk", "fi", "at", "ch",
}, key=len, reverse=True)
_COMPOUND = {
    "co.uk", "org.uk", "ac.uk", "gov.uk", "com.au", "net.au", "org.au", "co.jp",
    "co.kr", "com.br", "com.mx", "com.sg", "co.za", "com.cn", "com.hk", "co.in",
    "co.nz", "com.ar", "com.tr", "co.id", "com.ph",
}


def normalize_domain(domain: str | None) -> str | None:
    """acme.com, www.acme.co.uk, Acme-Corp.biz -> 'acme' or 'acmecorp'."""
    if not domain:
        return None
    d = domain.strip().lower().rstrip(".")
    d = d.replace("http://", "").replace("https://", "").split(";")[0].split(",")[0].split("/")[0]
    d = d.removeprefix("www.")
    parts = d.split(".")
    if not parts or parts[0] == "":
        return None
    depth = 2 if ".".join(parts[-2:]) in _COMPOUND else 1
    host = parts[:-depth]
    if not host:
        return None
    label = _CLEAN.sub("", ".".join(host))
    return label or None


def _name_tokens(name: str) -> set[str]:
    toks = set(_CLEAN.sub(" ", name.lower()).split())
    toks.discard("inc")
    toks.discard("llc")
    toks.discard("llp")
    toks.discard("the")
    toks.discard("ltd")
    toks.discard("co")
    toks.discard("corp")
    toks.discard("corp.")
    toks.discard("company")
    return toks


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def assign_dedup_keys(db: Session) -> None:
    """Compute dedup_key/group for every lead. Re-run after each scrape."""
    leads = db.query(Lead).all()
    for lead in leads:
        lead.dedup_key = normalize_domain(lead.domain or lead.website)


def group_duplicates(db: Session) -> dict[str, dict]:
    """Group leads into dedup clusters and mark primaries."""
    assign_dedup_keys(db)
    leads = db.query(Lead).all()

    domain_groups: dict[str, list[Lead]] = {}
    for lead in leads:
        key = lead.dedup_key
        if key:
            domain_groups.setdefault(key, []).append(lead)

    name_groups: dict[str, list[Lead]] = {}
    used: set[str] = set()
    for lead in leads:
        if lead.dedup_key:
            continue
        toks = _name_tokens(lead.company)
        if not toks:
            continue
        placed = False
        for group_key, group in name_groups.items():
            other_toks = _name_tokens(group[0].company)
            if _jaccard(toks, other_toks) >= 0.75:
                group.append(lead)
                placed = True
                break
        if not placed:
            name_groups[lead.company.lower()] = [lead]

    clusters: list[list[Lead]] = [g for g in domain_groups.values() if len(g) > 1] + \
                                  [g for g in name_groups.values() if len(g) > 1]

    report: dict[str, dict] = {}
    for cluster in clusters:
        ordered = sorted(cluster, key=lambda l: (l.completeness_score, l.confidence_score), reverse=True)
        primary = ordered[0]
        group_id = uuid.uuid4().hex[:12]
        for idx, lead in enumerate(ordered):
            lead.dedup_group = group_id
            lead.is_primary = idx == 0
            lead.duplicate_of_id = None if idx == 0 else primary.id
        report[group_id] = {
            "group_id": group_id,
            "primary": primary.to_dict(),
            "duplicates": [l.to_dict() for l in ordered[1:]],
        }
    db.commit()
    return report