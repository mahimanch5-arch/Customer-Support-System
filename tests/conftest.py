"""Test fixtures.

Each test runs against a fresh COPY of the seeded SQLite DB so mutating tests
(refunds, cancellations, goodwill credits) never interfere with each other or
corrupt the real fixtures. The commerce DB must be built first:

    bash _DB/build.sh            # or --minimal for just the eval fixtures
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
import pytest_asyncio

# High rate limit for tests — must be set before the app (and its middleware) import.
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000000"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = PROJECT_ROOT / "_DB" / "ecommerce.db"

# Fixture order numbers -> expectations, from the seeded eval cases.
FIXTURES = {
    "ORD-100001": {"customer_id": 1, "email": "jordan.lee@example.com",
                   "refund_verdict": "eligible_agent_can_approve", "order_value_cents": 6000},
    "ORD-100002": {"customer_id": 2, "refund_verdict": "outside_window"},
    "ORD-100003": {"customer_id": 3, "refund_verdict": "eligible_needs_human_approval"},
    "ORD-100004": {"customer_id": 4, "delay_credit_cents": 500},
    "ORD-100005": {"customer_id": 5, "status": "processing"},
    "ORD-100007": {"customer_id": 1, "refund_verdict": "blocked_prior_refund"},
    "ORD-100011": {"customer_id": 3, "refund_verdict": "blocked_open_dispute"},
}


@pytest.fixture(scope="session", autouse=True)
def _require_db():
    if not SOURCE_DB.exists():
        pytest.skip(f"Seeded DB not found at {SOURCE_DB}. Run: bash _DB/build.sh")


@pytest_asyncio.fixture
async def client(tmp_path):
    """An httpx AsyncClient bound to the app via in-process ASGI transport,
    pointed at a pristine per-test copy of the DB."""
    import httpx

    from app.core.config import settings
    from app.db.session import dispose_engine

    db_copy = tmp_path / "test.db"
    shutil.copy(SOURCE_DB, db_copy)
    settings.database_url = f"sqlite+aiosqlite:///{db_copy}"
    await dispose_engine()  # force a fresh engine bound to the copy

    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await dispose_engine()


# Convenience header builders.
PUBLIC = {"X-API-Key": "dev-public-key"}


def as_customer(customer_id: int) -> dict:
    return {**PUBLIC, "X-Customer-Id": str(customer_id)}


async def order_id_for(client, customer_id: int, order_number: str) -> int:
    r = await client.get(f"/api/v1/customers/{customer_id}/orders",
                         headers=as_customer(customer_id), params={"limit": 100})
    assert r.status_code == 200, r.text
    for o in r.json()["items"]:
        if o["order_number"] == order_number:
            return o["order_id"]
    raise AssertionError(f"{order_number} not found for customer {customer_id}")
