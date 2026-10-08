"""FastAPI application: SaaSquatch Prioritizer API."""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .config import CORS_ORIGINS
from .database import get_db, init_db
from .dedup import group_duplicates
from .models import Lead
from .scoring import score_lead
from .schemas import ScrapeRequest, ScrapeResult
from . import seed as seed_module

log = logging.getLogger("api")

init_db()

app = FastAPI(
    title="SaaSquatch Prioritizer API",
    version="1.0.0",
    description="Multi-source lead scraping + AI prioritization, dedup and validation.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ helpers

def _apply_filters(q, query, industry, country, tier, min_score, has_email, dedup_group):
    if query:
        like = f"%{query}%"
        q = q.filter(or_(Lead.company.ilike(like), Lead.owner_email.ilike(like)))
    if industry:
        q = q.filter(Lead.industry.ilike(f"%{industry}%"))
    if country:
        q = q.filter(Lead.country.ilike(country))
    if tier:
        q = q.filter(Lead.tier == tier)
    if min_score is not None:
        q = q.filter(Lead.priority_score >= min_score)
    if has_email:
        q = q.filter(Lead.owner_email.isnot(None))
    if dedup_group:
        q = q.filter(Lead.dedup_group == dedup_group)
    return q


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    return {"status": "ok", "leads": db.query(Lead).count()}


@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    total = db.query(Lead).count()
    if total == 0:
        return {"total": 0, "hot": 0, "warm": 0, "cold": 0, "duplicates": 0,
                "avg_confidence": 0, "avg_completeness": 0, "with_email": 0,
                "verified_emails": 0, "industries": [], "countries": []}
    hot = db.query(func.count(Lead.id)).filter(Lead.tier == "hot").scalar()
    warm = db.query(func.count(Lead.id)).filter(Lead.tier == "warm").scalar()
    cold = db.query(func.count(Lead.id)).filter(Lead.tier == "cold").scalar()
    dups = db.query(func.count(Lead.id)).filter(Lead.is_primary.is_(False)).scalar()
    avg_conf = db.query(func.avg(Lead.confidence_score)).scalar()
    avg_comp = db.query(func.avg(Lead.completeness_score)).scalar()
    with_email = db.query(func.count(Lead.id)).filter(Lead.owner_email.isnot(None)).scalar()
    verified = db.query(func.count(Lead.id)).filter(Lead.email_status == "verified").scalar()
    industries = [r[0] for r in db.query(Lead.industry).filter(Lead.industry.isnot(None)).distinct().order_by(Lead.industry).all()]
    countries = [r[0] for r in db.query(Lead.country).filter(Lead.country.isnot(None)).distinct().order_by(Lead.country).all()]
    return {
        "total": total, "hot": hot, "warm": warm, "cold": cold, "duplicates": dups,
        "avg_confidence": round(avg_conf or 0, 1), "avg_completeness": round(avg_comp or 0, 1),
        "with_email": with_email, "verified_emails": verified,
        "industries": industries, "countries": countries,
    }


@app.get("/api/leads")
def list_leads(
    q: str = "", industry: str = "", country: str = "", tier: str = "",
    min_score: float = 0.0, has_email: bool = False, dedup_group: str = "",
    sort: str = "priority_score", order: str = "desc",
    page: int = 1, per_page: int = 50,
    include_duplicates: bool = True,
    db: Session = Depends(get_db),
):
    query = db.query(Lead)
    query = _apply_filters(query, q, industry, country, tier or None,
                           min_score or None, has_email, dedup_group or None)
    if not include_duplicates:
        query = query.filter(Lead.is_primary.is_(True))

    sortable = {
        "priority_score": Lead.priority_score, "company": Lead.company,
        "employees": Lead.employees, "icp_score": Lead.icp_score,
        "confidence_score": Lead.confidence_score, "completeness_score": Lead.completeness_score,
        "revenue_estimate_usd": Lead.revenue_estimate_usd, "created_at": Lead.created_at,
    }
    col = sortable.get(sort, Lead.priority_score)
    query = query.order_by(col.desc() if order == "desc" else col.asc())

    total = query.count()
    leads = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "total": total, "page": page, "per_page": per_page,
        "leads": [l.to_dict() for l in leads],
    }


@app.get("/api/leads/{lead_id}")
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    return {"lead": lead.to_dict()}


@app.get("/api/report/dedup")
def dedup_report(db: Session = Depends(get_db)):
    report = group_duplicates(db)
    groups = [{"group_id": g["group_id"], "primary": g["primary"],
               "duplicates": g["duplicates"]} for g in report.values()]
    return {"count": len(groups), "groups": groups}


@app.post("/api/leads/{lead_id}/rescore")
def rescore(lead_id: str, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    score_lead(lead)
    db.commit()
    return {"lead": lead.to_dict()}


@app.post("/api/leads/{lead_id}/resolve")
def resolve(lead_id: str, db: Session = Depends(get_db)):
    """'Keep primary': delete duplicate records in the same dedup group."""
    lead = db.get(Lead, lead_id)
    if not lead or not lead.dedup_group:
        raise HTTPException(404, "Lead is not part of a dedup group")
    dups = db.query(Lead).filter(Lead.dedup_group == lead.dedup_group,
                                 Lead.is_primary.is_(False)).all()
    removed = len(dups)
    for d in dups:
        db.delete(d)
    if not lead.is_primary:
        lead.is_primary = True
        lead.duplicate_of_id = None
    db.commit()
    return {"resolved": lead.id, "removed_duplicates": removed}


@app.post("/api/scrape")
def scrape(body: ScrapeRequest, db: Session = Depends(get_db)):
    from .scraper import run_fixture, ADAPTERS, HtmlDirectoryAdapter, JsonRegistryAdapter

    parsed = 0
    deduped_post_scrape = 0
    new_leads = 0

    if body.mode == "fixture":
        for source_name, raws in run_fixture():
            for raw in raws:
                lead = seed_module.ingest_raw(db, raw, source_name)
                parsed += 1
                new_leads += 1 if lead else 0
    elif body.mode == "html":
        if not body.html:
            raise HTTPException(422, "html is required when mode='html'")
        adapter = ADAPTERS.get(body.source, HtmlDirectoryAdapter())()
        if isinstance(adapter, HtmlDirectoryAdapter):
            adapter = HtmlDirectoryAdapter("card_layout" if "record" in body.html else "table_layout")
        elif isinstance(adapter, JsonRegistryAdapter):
            adapter = JsonRegistryAdapter()
        raws = adapter.parse(body.html)
        for raw in raws:
            lead = seed_module.ingest_raw(db, raw, body.source)
            parsed += 1
            new_leads += 1 if lead else 0
    elif body.mode == "url":
        raise HTTPException(422, "URL scraping is disabled in the demo build "
                                 "(kept offline for reliability + safe scraping). "
                                 "Paste HTML or use fixture mode.")
    else:
        raise HTTPException(422, "Unknown mode")

    db.commit()
    leads = db.query(Lead).all()
    for lead in leads:
        score_lead(lead)
    db.commit()
    report = group_duplicates(db)
    return ScrapeResult(source=body.source, parsed=parsed,
                        deduplicated=sum(len(g["duplicates"]) for g in report.values()),
                        new_leads=new_leads, rejected=0)


@app.get("/api/export.csv")
def export_csv(
    q: str = "", industry: str = "", country: str = "", tier: str = "",
    min_score: float = 0.0, has_email: bool = False, include_duplicates: bool = True,
    sort: str = "priority_score", order: str = "desc",
    include_score: bool = True,
    db: Session = Depends(get_db),
):
    query = db.query(Lead)
    query = _apply_filters(query, q, industry, country, tier or None,
                           min_score or None, has_email, None)
    if not include_duplicates:
        query = query.filter(Lead.is_primary.is_(True))
    col = Lead.priority_score if sort == "priority_score" else Lead.company
    query = query.order_by(col.desc() if order == "desc" else col.asc())
    leads = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    header = ["company", "domain", "industry", "city", "country", "employees",
              "revenue_estimate_usd", "owner_name", "owner_email", "owner_phone",
              "company_phone", "linkedin", "website"]
    if include_score:
        header += ["priority_score", "tier", "icp_score", "completeness_score",
                   "confidence_score", "email_status", "phone_status"]
    writer.writerow(header)
    for lead in leads:
        row = [lead.company, lead.domain, lead.industry, lead.city, lead.country,
               lead.employees, lead.revenue_estimate_usd, lead.owner_name,
               lead.owner_email, lead.owner_phone, lead.company_phone,
               lead.company_linkedin, lead.website]
        if include_score:
            row += [round(lead.priority_score, 1), lead.tier, round(lead.icp_score, 1),
                    round(lead.completeness_score, 1), round(lead.confidence_score, 1),
                    lead.email_status, lead.phone_status]
        writer.writerow(row)

    from fastapi.responses import Response
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="prioritized_leads_{stamp}.csv"',
        },
    )


@app.on_event("startup")
def startup_seed():
    from .database import SessionLocal
    db = SessionLocal()
    try:
        if db.query(Lead).count() == 0:
            seed_module.seed(db)
    finally:
        db.close()