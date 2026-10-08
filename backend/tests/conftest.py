"""Shared pytest configuration.

Key design points:
  - Use an isolated throwaway SQLite DB (never touches backend/instance/).
  - Disable live DNS/MX lookups so the whole suite is deterministic and runs
    offline (mirrors the production "graceful degradation" behaviour).
"""

from __future__ import annotations

import os
import socket
import sys
import tempfile
from pathlib import Path

# 1) Point the app at an isolated DB BEFORE anything imports app.config.
_TMPDIR = tempfile.mkdtemp(prefix="saaquatch_tests_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test.db"

# 2) Make `app` importable regardless of CWD (`backend/tests/..`).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import seed as seed_module  # noqa: E402
from app.database import Base, engine, init_db, SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
import app.validation as validation  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def offline_network():
    """Disable DNS/MX + DNS host resolution for the entire session.

    validate_email / validate_domain degrade to deterministic offline statuses
    exactly like they do when the network is unavailable in production.
    """
    orig_dns = validation.dns
    orig_getaddrinfo = socket.getaddrinfo

    validation.dns = None
    socket.getaddrinfo = lambda *a, **k: (_ for _ in ()).throw(OSError())
    yield
    validation.dns = orig_dns
    socket.getaddrinfo = orig_getaddrinfo


@pytest.fixture()
def fresh_db():
    """A clean database for unit tests that touch the ORM directly."""
    Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture()
def client():
    """FastAPI TestClient against a freshly seeded database (37 leads)."""
    Base.metadata.drop_all(bind=engine)
    init_db()
    with TestClient(app) as c:  # startup event seeds the empty DB
        yield c


def seed_count(stats: dict) -> int:
    return stats["seeded"] + stats["scraped"]