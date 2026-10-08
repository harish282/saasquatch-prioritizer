"""Multi-source scraping pipeline.

Runs fully offline against bundled fixtures so the demo is deterministic, but the
selector-driven adapters genuinely parse HTML/JSON — the same code path handles
"changing website structures" by swapping selector configs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable

from selectolax.lexbor import LexborHTMLParser as HTMLParser

from .config import FIXTURES_DIR

_CLEAN_TXT = re.compile(r"\s+")
_DIGITS = re.compile(r"[0-9]+")


@dataclass
class RawLead:
    company: str
    domain: str | None = None
    website: str | None = None
    industry: str | None = None
    city: str | None = None
    country: str | None = None
    employees: int | None = None
    owner_first_name: str | None = None
    owner_last_name: str | None = None
    owner_email: str | None = None
    owner_phone: str | None = None
    company_phone: str | None = None
    company_linkedin: str | None = None
    description: str | None = None
    source_url: str | None = None
    skip: bool = False
    skip_reason: str = ""


def _text(node, selector: str | None) -> str:
    if node is None or not selector:
        return ""
    el = node  # css on root
    sel = selector
    try:
        found = el.css(sel)
    except Exception:
        found = []
    if not found:
        return ""
    return _CLEAN_TXT.sub(" ", found[0].text()).strip()


def _attr(node, selector: str, attribute: str, ) -> str:
    if node is None or not selector:
        return ""
    try:
        found = node.css(selector)
    except Exception:
        return ""
    if not found:
        return ""
    return (found[0].attributes or {}).get(attribute, "").strip()


def _first_int(text: str | None) -> int | None:
    if not text:
        return None
    nums = _DIGITS.findall(text)
    if not nums:
        return None
    return int(nums[0])


def _validate_company(company: str | None) -> bool:
    return bool(company and company.strip()) and company.strip().lower() not in {
        "none", "n/a", "-", "", "private co ltd", "unknown business"}


# ---------------------------------------------------------------- Adapters

class SourceAdapter:
    name: str = "base"
    record_selector: str = ""

    def parse(self, content: str) -> list[RawLead]:
        raise NotImplementedError

    def _extract(self, node, cfg: dict[str, str], source_url: str) -> RawLead:
        raise NotImplementedError


class HtmlDirectoryAdapter(SourceAdapter):
    """CSS-selector driven parser. Swapping `card`/field selectors adapts to a
    completely different site layout — 'changing website structures' handled."""

    name = "business_directory"

    CARD_CONFIGS: dict[str, dict[str, str]] = {
        "card_layout": {
            "record": "div.record",
            "company": ".company-name",
            "website": "a.website",
            "industry": ".industry",
            "city": ".city",
            "country": ".country",
            "employees": ".employees",
            "owner": ".owner",
            "owner_email": ".owner-email",
            "phone": ".phone",
            "linkedin": "a.linkedin",
            "description": ".description",
            "link": "a.record-link",
        },
        "table_layout": {
            "record": "tr.lead-row",
            "company": "td:first-child .name",
            "website": "td:nth-child(2) a",
            "industry": "td:nth-child(3)",
            "city": "td:nth-child(4)",
            "country": "td:nth-child(5)",
            "employees": "td:nth-child(6)",
            "owner": "td:nth-child(7)",
            "owner_email": "td:nth-child(8)",
            "phone": "td:nth-child(9)",
            "linkedin": "td:nth-child(2) a.link-in",
            "description": "td:first-child .desc",
            "link": "a",
        },
    }

    def __init__(self, layout: str = "card_layout"):
        self.layout = layout
        cfg = self.CARD_CONFIGS[layout]
        self.record_selector = cfg["record"]
        self.cfg = cfg

    def parse(self, content: str) -> list[RawLead]:
        tree = HTMLParser(content)
        records = tree.css(self.record_selector)
        leads = []
        for idx, record in enumerate(records):
            lead = self._extract(record)
            lead.source_url = f"fixture:{self.layout}#{idx}"
            leads.append(lead)
        return leads

    def _extract(self, node) -> RawLead:
        cfg = self.cfg
        owner_phone = _text(node, cfg["phone"])
        owner_line = _text(node, cfg["owner"])
        first, last = _split_owner(owner_line)
        website = _attr(node, cfg["website"], "href") or _text(node, cfg["website"])
        raw = RawLead(
            company=_text(node, cfg["company"]),
            website=website,
            domain=website,
            industry=_text(node, cfg["industry"]),
            city=_text(node, cfg["city"]),
            country=_text(node, cfg["country"]),
            employees=_first_int(_text(node, cfg["employees"])),
            owner_first_name=first,
            owner_last_name=last,
            owner_email=_text(node, cfg["owner_email"]),
            company_phone=owner_phone,
            company_linkedin=_attr(node, cfg["linkedin"], "href") or _text(node, cfg["linkedin"]),
            description=_text(node, cfg["description"]),
        )
        raw.company = raw.company.strip()
        raw.country = _normalize_country(raw.country)
        raw.domain = _clean_domain(raw.website)
        if not _validate_company(raw.company):
            raw.skip, raw.skip_reason = True, "No company name"
        return raw


class JsonRegistryAdapter(SourceAdapter):
    """Parses structured record lists (registry exports, APIs, LLM-generated docs)."""

    name = "public_registry"

    def __init__(self, country_field: str = "country"):
        self.country_field = country_field

    def parse(self, content: str) -> list[RawLead]:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return []
        records = data if isinstance(data, list) else data.get("records") or data.get("results") or []
        leads = []
        for idx, rec in enumerate(records):
            if not isinstance(rec, dict):
                continue
            owner = rec.get("owner") or rec.get("contact") or {}
            website = rec.get("website") or rec.get("web") or rec.get("domain") or ""
            raw = RawLead(
                company=str(rec.get("name") or rec.get("company") or "").strip(),
                website=website,
                domain=website,
                industry=(rec.get("industry") or "").strip(),
                city=(rec.get("city") or "").strip(),
                country=_normalize_country(str(rec.get(self.country_field) or "").strip()),
                employees=_first_int(str(rec.get("employees") or rec.get("employee_count") or "")),
                owner_first_name=(owner.get("first_name") or "").strip(),
                owner_last_name=(owner.get("last_name") or "").strip(),
                owner_email=(owner.get("email") or rec.get("email") or "").strip() or None,
                owner_phone=(owner.get("phone") or "").strip() or None,
                company_phone=(rec.get("phone") or "").strip() or None,
                company_linkedin=(rec.get("linkedin") or "").strip() or None,
                description=(rec.get("description") or "").strip() or None,
                source_url=f"fixture:public_registry#{idx}",
            )
            raw.domain = _clean_domain(raw.website)
            if not _validate_company(raw.company):
                raw.skip, raw.skip_reason = True, "No company name"
            leads.append(raw)
        return leads


# ---------------------------------------------------------------- Read + helpers

ADAPTERS: dict[str, Callable[[], SourceAdapter]] = {
    "business_directory": lambda: HtmlDirectoryAdapter("card_layout"),
    "business_directory_table": lambda: HtmlDirectoryAdapter("table_layout"),
    "public_registry": lambda: JsonRegistryAdapter(),
}


def _split_owner(line: str) -> tuple[str | None, str | None]:
    parts = [p for p in _CLEAN_TXT.sub(" ", line or "").split() if p]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[-1]


_COUNTRY_MAP = {
    "usa": "USA", "us": "USA", "united states": "USA", "america": "USA",
    "canada": "CANADA", "can": "CANADA",
    "uk": "UNITED KINGDOM", "gb": "UNITED KINGDOM", "great britain": "UNITED KINGDOM",
    "england": "UNITED KINGDOM",
    "germany": "GERMANY", "de": "GERMANY", "france": "FRANCE", "fr": "FRANCE",
    "australia": "AUSTRALIA", "au": "AUSTRALIA", "india": "INDIA", "in": "INDIA",
    "new zealand": "NEW ZEALAND", "nz": "NEW ZEALAND",
}


def _normalize_country(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip()
    norm = _COUNTRY_MAP.get(v.lower(), v.upper())
    return norm or None


def _clean_domain(value: str | None) -> str | None:
    if not value:
        return None
    d = value.strip().lower().rstrip("/").replace("http://", "").replace("https://", "")
    d = d.removeprefix("www.").split("?")[0].split("/")[0].split("#")[0]
    # keep the hostname, e.g. acme.com OR www.acme.co.uk
    if d.count(".") >= 2 and not d.split(".")[-1] in ("uk", "au", "jp", "uk.com"):
        pass
    return d or None


def run_fixture(mode: str | None = None) -> list[tuple[str, list[RawLead]]]:
    """Returns [(source_name, [RawLead])] from bundled fixtures."""
    results = []
    fixtures = []

    if mode in (None, "card"):
        fixtures.append(("business_directory", FIXTURES_DIR / "business_directory.html"))
        fixtures.append(("business_directory_table", FIXTURES_DIR / "business_directory_table.html"))
        fixtures.append(("public_registry", FIXTURES_DIR / "public_registry.json"))
    else:
        fixtures.append((mode, FIXTURES_DIR / f"{mode}.html" if mode in (
            "business_directory", "business_directory_table") else FIXTURES_DIR / f"{mode}.json"))

    for source_name, path in fixtures:
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8")
        adapter_name = source_name
        if source_name == "business_directory_table":
            adapter_name = "business_directory"
        adapter = ADAPTERS[adapter_name]()
        if adapter.name == "business_directory" and "table" in source_name:
            adapter = HtmlDirectoryAdapter("table_layout")
        if adapter_name == "public_registry":
            adapter = JsonRegistryAdapter()
        parsed = adapter.parse(content)
        results.append((source_name, parsed))
    return results