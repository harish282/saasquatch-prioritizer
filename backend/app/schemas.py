"""Pydantic schemas for request/response bodies."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SourceInput(BaseModel):
    source: str
    url: str | None = None
    captured_at: str | None = None


class ScrapeRequest(BaseModel):
    mode: Literal["fixture", "html", "url"]
    source: str = Field(default="business_directory", description="Which source adapter to use")
    html: str | None = Field(default=None, description="Raw HTML for mode='html'")
    url: str | None = Field(default=None, description="URL for mode='url' (may be disabled)")


class ScrapedLeadOut(BaseModel):
    company: str
    domain: str | None = None
    website: str | None = None
    industry: str | None = None
    city: str | None = None
    country: str | None = None
    employees: int | None = None
    owner_name: str | None = None
    owner_email: str | None = None
    owner_phone: str | None = None
    company_phone: str | None = None
    company_linkedin: str | None = None


class ScrapeResult(BaseModel):
    source: str
    parsed: int
    deduplicated: int
    new_leads: int
    rejected: int


class TierFilter(BaseModel):
    tier: Literal["hot", "warm", "cold"] | None = None