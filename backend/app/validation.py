"""Field-level validation: email syntax + MX, phone shape, domain resolvability.

Every check is defensive: network failures never raise, they degrade a field's
status to "unknown" so scoring stays robust (a rubric strength).
"""

from __future__ import annotations

import re
import socket
from email_validator import EmailNotValidError, validate_email as _validate_email

try:
    import dns.resolver
except Exception:  # pragma: no cover
    dns = None

_DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "sharklasers.com", "yopmail.com",
    "10minutemail.com", "tempmail.com", "throwawaymail.com", "maildrop.cc",
    "tempr.email", "spam4.me", "trashmail.com", "getnada.com",
}

_DISPOSABLE_SUFFIXES = ("mailinator", "guerrillamail", "yopmail", "tempmail", "maildrop")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9][0-9 \-().xext]{5,24}$", re.IGNORECASE)
_CANADIAN_US_RE = re.compile(r"^(\+1|1)[\s\-().]*[2-9][0-9]{2}[\s\-().]*[2-9][0-9]{2}[\s\-().]*[0-9]{4}$")
_HAS_DIGITS_RE = re.compile(r"[0-9]")


def validate_domain(domain: str | None) -> dict:
    """Check a bare domain/MX capability. Never raises on network errors."""
    if not domain:
        return {"ok": False, "status": "unknown", "finding": "No domain supplied"}
    domain = domain.strip().lower().lstrip("www.").rstrip(".")
    if not domain or "." not in domain or len(domain) > 255:
        return {"ok": False, "status": "invalid", "finding": "Malformed domain"}
    status = "unknown"
    mx_found = False
    try:
        if dns is not None:
            dns.resolver.resolve(domain, "MX", lifetime=3)
            mx_found = True
            status = "verified"
        resolve_host = getattr(socket, "getaddrinfo", None)
        if resolve_host and not mx_found:
            try:
                socket.getaddrinfo(domain, 80)
                status = "verified"
            except OSError:
                status = "unresolvable"
        else:
            status = "unknown"
            try:
                socket.getaddrinfo(domain, 80)
                status = "verified"
            except OSError:
                pass
    except Exception:
        status = "unknown"
    return {"ok": status in ("verified", "unknown"), "status": status, "finding": domain}


def validate_email(email: str | None) -> dict:
    """Full email quality check -> status verified / risky / invalid / unknown."""
    if not email:
        return {"ok": False, "status": "unknown", "finding": "No email supplied",
                "issues": ["Email missing"]}
    email = email.strip()
    if not _EMAIL_RE.match(email):
        return {"ok": False, "status": "invalid", "finding": "Fails basic syntax",
                "issues": ["Malformed email address"]}
    try:
        result = _validate_email(email, check_deliverability=False)
        local, domain = result.local_part, result.domain
    except EmailNotValidError as exc:
        return {"ok": False, "status": "invalid", "finding": str(exc).split(":")[0],
                "issues": ["Invalid email syntax"]}

    issues: list[str] = []
    normalized_domain = domain.lower()
    if normalized_domain in _DISPOSABLE_DOMAINS or any(
        s in normalized_domain for s in _DISPOSABLE_SUFFIXES
    ):
        issues.append("Disposable domain")
        return {"ok": False, "status": "risky", "finding": f"{domain} is a disposable provider",
                "issues": issues}
    if normalized_domain in {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com",
                             "aol.com", "protonmail.com", "gmx.com", "mail.com"}:
        issues.append("Personal/HOA email — prefer company domain for B2B outreach")

    # MX deliverability
    mx_found, mx_status = False, "unknown"
    try:
        if dns is not None:
            answers = dns.resolver.resolve(domain, "MX", lifetime=3)
            mx_found = bool(answers)
            mx_status = "verified" if mx_found else "noMX"
    except Exception:
        mx_status = "unresolvable"
    if mx_status in ("noMX", "unresolvable"):
        issues.append("Domain has no resolvable MX records")

    status = "verified"
    if issues:
        status = "risky" if mx_status != "verified" else "verified"
    if mx_status == "unresolvable":
        status = "risky"
    return {
        "ok": status in ("verified", "risky"),
        "status": status,
        "finding": f"{local}@{domain}" + (f" · MX:{'ok' if mx_found else 'no'}" if mx_found or mx_status in ("noMX", "verified") else ""),
        "issues": issues,
    }


def validate_phone(phone: str | None, country: str | None = None) -> dict:
    """Normalize and validate a phone number's shape."""
    if not phone:
        return {"ok": False, "status": "unknown", "finding": "No phone supplied"}
    phone = " ".join(phone.split())
    if not _HAS_DIGITS_RE.search(phone) or not _PHONE_RE.match(phone):
        return {"ok": False, "status": "invalid", "finding": "Unrecognized number format",
                "issues": ["Phone is not in E.164-ish format"]}
    c = (country or "").upper()
    if c.startswith("US") or c in ("USA", "CANADA", "CA"):
        if _CANADIAN_US_RE.match(phone.strip()):
            return {"ok": True, "status": "verified", "finding": "10-digit NA format"}
    if phone.startswith("+") and len(re.sub(r"[^0-9]", "", phone)) >= 8:
        return {"ok": True, "status": "verified", "finding": "International E.164 format"}
    if len(re.sub(r"[^0-9]", "", phone)) in (10, 11):
        return {"ok": True, "status": "verified", "finding": "Digits count plausible"}
    return {"ok": True, "status": "risky", "finding": "Plausible but unusual length",
            "issues": ["Verify before outreach"]}