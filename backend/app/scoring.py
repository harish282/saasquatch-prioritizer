"""Scoring engine.

Three explainable sub-scores feed a composite priority score:
  - ICP fit: how well the lead matches a searcher/ETA buyer profile
  - Completeness: share of high-value fields populated
  - Confidence: validation status of emails/phones + multi-source corroboration
  - Freshness: decay based on when the record was captured
"""

from __future__ import annotations

from datetime import datetime, timezone

from .config import ICP, PRIORITY_WEIGHTS
from .models import Lead
from .validation import validate_domain, validate_email, validate_phone


def _icp_score(lead: Lead) -> dict:
    parts: dict[str, float] = {}
    notes: list[str] = []

    country = (lead.country or "").upper()
    if not country:
        parts["country"] = 50.0
        notes.append("Country unknown (neutral)")
    elif country in {c.upper() for c in ICP["preferred_countries"]}:
        parts["country"] = 100.0
        notes.append(f"{country or lead.country}: target market")
    else:
        parts["country"] = 45.0
        notes.append(f"{lead.country}: outside target geography")

    industry = (lead.industry or "").strip().lower()
    _corp_markers = ("group", "corporation", "corporate", "gmbh", "holdings",
                     "global", "industrial", "international", "plc", "public co")
    if not industry:
        parts["industry"] = 50.0
        notes.append("Industry unknown (neutral)")
    elif any(marker in industry for marker in _corp_markers):
        parts["industry"] = 55.0
        notes.append(f"{lead.industry}: corporate-wide category — weak fit")
    elif any(pref in industry for pref in ICP["preferred_industries"]):
        parts["industry"] = 100.0
        notes.append(f"{lead.industry}: high-fit service/SMB vertical")
    else:
        parts["industry"] = 60.0
        notes.append(f"{lead.industry}: accepted vertical")

    emp = lead.employees
    lo, hi = ICP["ideal_employee_min"], ICP["ideal_employee_max"]
    if emp is None:
        parts["size"] = 50.0
        notes.append("Employee count unknown (neutral)")
    elif lo <= emp <= hi:
        parts["size"] = 95.0
        notes.append(f"{emp} employees: founder-operated SMB sweet spot")
    elif emp < lo:
        parts["size"] = 60.0
        notes.append(f"{emp} employees: very small, verify readiness")
    elif emp <= 2000:
        parts["size"] = 45.0
        notes.append(f"{emp} employees: too large for a search-fund profile")
    else:
        parts["size"] = 15.0
        notes.append(f"{emp} employees: corporate — out of market for a searcher")

    has_web = bool(lead.website or lead.domain or lead.company_linkedin)
    parts["web_presence"] = 100.0 if has_web else 30.0
    notes.append("Web presence established" if has_web else "Little/no web presence")

    rev = lead.revenue_estimate_usd
    if rev is None:
        parts["revenue"] = 50.0
        notes.append("Revenue estimate unavailable (neutral)")
    elif ICP["revenue_floor_usd"] <= rev <= ICP["revenue_ideal_usd"]:
        parts["revenue"] = 90.0
        notes.append(f"${rev:,.0f} est. revenue: within acquisition range")
    elif ICP["revenue_ideal_usd"] < rev <= ICP["revenue_ideal_usd"] * 20:
        parts["revenue"] = 65.0
        notes.append(f"${rev:,.0f} est. revenue: beyond typical search target")
    elif rev > ICP["revenue_ideal_usd"] * 20:
        parts["revenue"] = 35.0
        notes.append(f"${rev:,.0f} est. revenue: corporate-scale, not dealable")
    else:
        parts["revenue"] = 55.0
        notes.append(f"${rev:,.0f} est. revenue: below target floor")

    weight_map = {
        "country": ICP["country_weight"],
        "industry": ICP["industry_weight"],
        "size": ICP["size_weight"],
        "web_presence": ICP["web_weight"],
        "revenue": ICP["revenue_weight"],
    }
    total = sum(parts[k] * weight_map[k] for k in weight_map if k in parts)
    score = round(total / sum(weight_map.values()), 1)
    return {"score": score, "breakdown": {k: round(v, 1) for k, v in parts.items()},
            "notes": notes}


def _completeness(lead: Lead) -> dict:
    fields = [
        ("company", bool(lead.company), 20.0),
        ("industry", bool(lead.industry), 10.0),
        ("location", bool(lead.city and lead.country), 12.0),
        ("size", lead.employees is not None, 12.0),
        ("owner_name", bool(lead.owner_first_name or lead.owner_last_name), 8.0),
        ("owner_email", bool(lead.owner_email), 18.0),
        ("phone", bool(lead.owner_phone or lead.company_phone), 10.0),
        ("web_presence", bool(lead.website or lead.domain or lead.company_linkedin), 10.0),
    ]
    populated = [name for name, has, _weight in fields if has]
    total = sum(w for _n, _h, w in fields)
    earned = sum(w for _n, has, w in fields if has)
    score = round(earned / total * 100, 1)
    missing = [name for name, has, _w in fields if not has]
    return {"score": score, "populated": populated, "missing": missing}


def _confidence(lead: Lead) -> dict:
    sub: dict[str, float] = {}
    ev = validate_email(lead.owner_email) if lead.owner_email else {"status": "unknown"}
    if lead.owner_email:
        mapping = {"verified": 100.0, "risky": 55.0, "invalid": 5.0, "unknown": 45.0}
        sub["email"] = mapping.get(ev["status"], 45.0)
        email_status = ev["status"] if ev["status"] != "unknown" else "unknown"
    else:
        sub["email"] = 0.0
        email_status = "unknown"

    phone = lead.owner_phone or lead.company_phone
    if phone:
        pv = validate_phone(phone, lead.country)
        mapping = {"verified": 100.0, "risky": 55.0, "invalid": 15.0, "unknown": 45.0}
        sub["phone"] = mapping.get(pv["status"], 45.0)
        phone_status = "unknown" if pv["status"] == "unknown" else (
            "verified" if pv["status"] == "verified" else "risky")
    else:
        sub["phone"] = 0.0
        phone_status = "unknown"

    dv = validate_domain(lead.domain or lead.website)
    sub["domain"] = {"verified": 100.0, "risky": 50.0, "invalid": 10.0,
                     "unknown": 40.0}.get(dv["status"], 40.0) if (lead.domain or lead.website) else 0.0

    source_count = len(lead.sources or [])
    if source_count >= 3:
        sub["corroboration"] = 100.0
    elif source_count == 2:
        sub["corroboration"] = 80.0
    elif source_count == 1:
        sub["corroboration"] = 55.0
    else:
        sub["corroboration"] = 30.0

    weights = {"email": 0.4, "phone": 0.25, "domain": 0.15, "corroboration": 0.2}
    score = round(sum(sub[k] * w for k, w in weights.items()), 1)

    # Outreachability gate: a lead nobody can reach is not a priority, however
    # well it fits the ICP. Cap confidence when both channels are missing.
    if not lead.owner_email and not (lead.owner_phone or lead.company_phone):
        score = min(score, 22.0)

    return {"score": score, "breakdown": {k: round(v, 1) for k, v in sub.items()},
            "email_status": email_status, "phone_status": phone_status,
            "validation": ev}


def _freshness(lead: Lead) -> float:
    base = lead.captured_at if lead.captured_at else lead.created_at
    if base is None:
        return 1.0
    now = datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    age_days = max(0.0, (now - base).total_seconds() / 86400)
    if age_days <= 30:
        return 1.0
    if age_days <= 90:
        return 0.9
    if age_days <= 180:
        return 0.7
    return 0.5


def _tier(score: float) -> str:
    if score >= 80:
        return "hot"
    if score >= 55:
        return "warm"
    return "cold"


def score_lead(lead: Lead) -> Lead:
    """Compute all quality signals in-place and return the lead."""
    icp = _icp_score(lead)
    completeness = _completeness(lead)
    confidence = _confidence(lead)

    f = _freshness(lead)
    priority = round(
        icp["score"] * PRIORITY_WEIGHTS["icp"]
        + completeness["score"] * PRIORITY_WEIGHTS["completeness"]
        + confidence["score"] * PRIORITY_WEIGHTS["confidence"]
        + f * 100 * PRIORITY_WEIGHTS["freshness"],
        1,
    )

    # ICP market gate: a lead outside the target profile can never rank hot or
    # (for a true out-of-market record) even warm, however pristine its data is.
    if icp["score"] < 60:
        priority = min(priority, 54.9)
        icp["notes"].append("MARKET GATE: record is outside the search-fund ICP")
    elif icp["score"] < 75:
        priority = min(priority, 79.9)
        icp["notes"].append("MARKET GATE: capped at warm — partial ICP fit only")

    lead.icp_score = icp["score"]
    lead.completeness_score = completeness["score"]
    lead.confidence_score = confidence["score"]
    lead.freshness_score = round(f, 2)
    lead.priority_score = priority
    lead.tier = _tier(priority)
    lead.email_status = (lead.owner_email and confidence["email_status"]) or "none"
    lead.phone_status = confidence["phone_status"]
    lead.validation_detail = {
        "email": confidence.get("validation", {}) if lead.owner_email else {
            "status": "unknown", "finding": "No email supplied"},
        "phone": validate_phone(lead.owner_phone or lead.company_phone, lead.country),
        "domain": validate_domain(lead.domain or lead.website) if (lead.domain or lead.website) else {
            "status": "unknown", "finding": "No web presence to validate"},
    }
    lead.score_breakdown = {
        "priority": {
            "score": priority,
            "weights": {k: v for k, v in PRIORITY_WEIGHTS.items()},
            "components": {
                "icp": icp["score"], "completeness": completeness["score"],
                "confidence": confidence["score"], "freshness": f * 100,
            },
        },
        "icp": {"score": icp["score"], "breakdown": icp["breakdown"], "notes": icp["notes"]},
        "completeness": {"score": completeness["score"], "populated": completeness["populated"],
                         "missing": completeness["missing"]},
        "confidence": {"score": confidence["score"], "breakdown": confidence["breakdown"]},
    }
    if not lead.owner_email:
        lead.email_status = "missing"
    return lead