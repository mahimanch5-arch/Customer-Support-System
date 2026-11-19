"""Refund policy: eligibility verdicts + the confirmation / $100 / idempotency rules."""
from __future__ import annotations

import pytest

from tests.conftest import as_customer, order_id_for


@pytest.mark.parametrize("order_number,customer_id,expected", [
    ("ORD-100001", 1, "eligible_agent_can_approve"),
    ("ORD-100002", 2, "outside_window"),
    ("ORD-100003", 3, "eligible_needs_human_approval"),
    ("ORD-100007", 1, "blocked_prior_refund"),
    ("ORD-100011", 3, "blocked_open_dispute"),
])
async def test_refund_eligibility_verdicts(client, order_number, customer_id, expected):
    oid = await order_id_for(client, customer_id, order_number)
    r = await client.get(f"/api/v1/orders/{oid}/refund-eligibility", headers=as_customer(customer_id))
    assert r.status_code == 200, r.text
    assert r.json()["refund_verdict"] == expected


async def test_refund_requires_confirmation(client):
    oid = await order_id_for(client, 1, "ORD-100001")
    r = await client.post(f"/api/v1/orders/{oid}/refunds", headers=as_customer(1),
                          json={"reason": "changed my mind", "customer_confirmed": False})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "confirmation_required"


async def test_refund_issue_then_blocked_one_per_order(client):
    oid = await order_id_for(client, 1, "ORD-100001")
    r = await client.post(f"/api/v1/orders/{oid}/refunds", headers=as_customer(1),
                          json={"reason": "changed my mind", "customer_confirmed": True})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "issued"
    assert body["refund"]["approved_by_type"] == "ai_agent"
    # One refund per order: eligibility now blocked.
    r2 = await client.get(f"/api/v1/orders/{oid}/refund-eligibility", headers=as_customer(1))
    assert r2.json()["refund_verdict"] == "blocked_prior_refund"


async def test_refund_idempotency_replays(client):
    oid = await order_id_for(client, 1, "ORD-100001")
    hdr = {**as_customer(1), "Idempotency-Key": "refund-abc-123"}
    payload = {"reason": "changed my mind", "customer_confirmed": True}
    r1 = await client.post(f"/api/v1/orders/{oid}/refunds", headers=hdr, json=payload)
    r2 = await client.post(f"/api/v1/orders/{oid}/refunds", headers=hdr, json=payload)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["refund"]["refund_id"] == r2.json()["refund"]["refund_id"]


async def test_refund_over_100_escalates(client):
    # ORD-100003 is $140 -> eligible but needs human approval; must NOT auto-issue.
    oid = await order_id_for(client, 3, "ORD-100003")
    r = await client.post(f"/api/v1/orders/{oid}/refunds", headers=as_customer(3),
                          json={"reason": "defective", "customer_confirmed": True})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "pending_approval"
    assert body["refund"]["status"] == "pending"
    assert body["refund"]["requires_approval"] is True
    assert body["ticket_number"].startswith("TKT-")


async def test_refund_blocked_open_dispute(client):
    # ORD-100011 has an open chargeback -> must decline (PAY-004).
    oid = await order_id_for(client, 3, "ORD-100011")
    r = await client.post(f"/api/v1/orders/{oid}/refunds", headers=as_customer(3),
                          json={"reason": "want my money back", "customer_confirmed": True})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "refund_blocked_open_dispute"
