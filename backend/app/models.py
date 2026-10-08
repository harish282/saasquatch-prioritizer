"""ORM models for leads and their derived quality signals."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uuid)
    company: Mapped[str] = mapped_column(String(255), index=True)
    domain: Mapped[str | None] = mapped_column(String(255), index=True, default=None)
    website: Mapped[str | None] = mapped_column(String(512), default=None)
    industry: Mapped[str | None] = mapped_column(String(128), index=True, default=None)
    city: Mapped[str | None] = mapped_column(String(128), default=None)
    country: Mapped[str | None] = mapped_column(String(128), index=True, default=None)
    employees: Mapped[int | None] = mapped_column(Integer, default=None)
    revenue_estimate_usd: Mapped[float | None] = mapped_column(Float, default=None)
    owner_first_name: Mapped[str | None] = mapped_column(String(128), default=None)
    owner_last_name: Mapped[str | None] = mapped_column(String(128), default=None)
    owner_email: Mapped[str | None] = mapped_column(String(320), index=True, default=None)
    owner_phone: Mapped[str | None] = mapped_column(String(64), default=None)
    company_phone: Mapped[str | None] = mapped_column(String(64), default=None)
    company_linkedin: Mapped[str | None] = mapped_column(String(512), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    # Derived quality signals (computed by the scoring engine at ingest).
    icp_score: Mapped[float] = mapped_column(Float, default=0.0)
    completeness_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    freshness_score: Mapped[float] = mapped_column(Float, default=1.0)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    tier: Mapped[str] = mapped_column(String(16), default="cold", index=True)

    email_status: Mapped[str] = mapped_column(String(16), default="unknown")
    phone_status: Mapped[str] = mapped_column(String(16), default="unknown")

    # Per-field explainability: {"email_ok": bool, "finding": str, "issues": [str]}
    validation_detail: Mapped[dict | None] = mapped_column(JSON, default=dict)
    # Composite breakdown for the drawer: {"icp": {"industry": 80, ...}, ...}
    score_breakdown: Mapped[dict | None] = mapped_column(JSON, default=dict)
    # Which sources produced this lead: [{"source": str, "url": str, "captured_at": str}]
    sources: Mapped[list | None] = mapped_column(JSON, default=list)
    # Dedup: normalized domain key + fuzzy group id
    dedup_key: Mapped[str | None] = mapped_column(String(255), index=True, default=None)
    dedup_group: Mapped[str | None] = mapped_column(String(32), index=True, default=None)
    is_primary: Mapped[bool] = mapped_column(default=True)
    duplicate_of_id: Mapped[str | None] = mapped_column(String(32), default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    @property
    def owner_name(self) -> str | None:
        parts = [p for p in (self.owner_first_name, self.owner_last_name) if p]
        return " ".join(parts) if parts else None

    @property
    def email_status_label(self) -> str:
        labels = {"verified": "Verified", "risky": "Risky", "invalid": "Invalid", "unknown": "Unchecked"}
        return labels.get(self.email_status, self.email_status)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "company": self.company,
            "domain": self.domain,
            "website": self.website,
            "industry": self.industry,
            "city": self.city,
            "country": self.country,
            "employees": self.employees,
            "revenue_estimate_usd": self.revenue_estimate_usd,
            "owner_name": self.owner_name,
            "owner_email": self.owner_email,
            "owner_phone": self.owner_phone,
            "company_phone": self.company_phone,
            "company_linkedin": self.company_linkedin,
            "description": self.description,
            "icp_score": round(self.icp_score, 1),
            "completeness_score": round(self.completeness_score, 1),
            "confidence_score": round(self.confidence_score, 1),
            "freshness_score": round(self.freshness_score, 2),
            "priority_score": round(self.priority_score, 1),
            "tier": self.tier,
            "email_status": self.email_status,
            "email_status_label": self.email_status_label,
            "phone_status": self.phone_status,
            "validation_detail": self.validation_detail or {},
            "score_breakdown": self.score_breakdown or {},
            "sources": self.sources or [],
            "dedup_key": self.dedup_key,
            "dedup_group": self.dedup_group,
            "is_primary": self.is_primary,
            "duplicate_of_id": self.duplicate_of_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }