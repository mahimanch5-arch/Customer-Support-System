"""Returns, cancellation, goodwill credit, claims, tickets."""
from __future__ import annotations

from tests.conftest import as_customer, order_id_for


async def test_return_eligibility_within_window(client):
    oid = await order_id_for(client, 1, "ORD-100001")
    r = await client.get(f"/api/v1/orders/{oid}/return-eligibility", headers=as_customer(1))
    assert r.status_code == 200
    body = r.json()
    assert body["within_window"] is True
    assert len(body["items"]) >= 1


async def test_cancellation_rules(client):
    # Delivered order cannot be cancelled.
    delivered = await order_id_for(client, 1, "ORD-100001")
    r = await client.get(f"/api/v1/orders/{delivered}/cancellation-eligibility", headers=as_customer(1))
    assert r.status_code == 200 and r.json()["eligible"] is False

    # Processing order can be cancelled, and the action succeeds on confirmation.
    processing = await order_id_for(client, 5, "ORD-100005")
    r = await client.get(f"/api/v1/orders/{processing}/cancellation-eligibility", headers=as_customer(5))
    assert r.json()["eligible"] is True
    r2 = await client.post(f"/api/v1/orders/{processing}/cancel", headers=as_customer(5),
                           json={"reason": "no longer needed", "customer_confirmed": True})
    assert r2.status_code == 200, r2.text
    assert r2.json()["status"] == "cancelled"


async def test_cancel_requires_confirmation(client):
    processing = await order_id_for(client, 5, "ORD-100005")
    r = await client.post(f"/api/v1/orders/{processing}/cancel", headers=as_customer(5),
                          json={"reason": "no longer needed", "customer_confirmed": False})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "confirmation_required"


async def test_delay_goodwill_once_only(client):
    # ORD-100004 is 4 days late -> $5 (500c) credit; a second grant is refused.
    oid = await order_id_for(client, 4, "ORD-100004")
    r = await client.post(f"/api/v1/orders/{oid}/goodwill-credit", headers=as_customer(4), json={})
    assert r.status_code == 201, r.text
    assert r.json()["credit"]["cents"] == 500
    r2 = await client.post(f"/api/v1/orders/{oid}/goodwill-credit", headers=as_customer(4), json={})
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "goodwill_already_given"


async def test_create_claim(client):
    oid = await order_id_for(client, 1, "ORD-100001")
    r = await client.post(f"/api/v1/orders/{oid}/claims", headers=as_customer(1),
                          json={"type": "damaged", "description": "Arrived cracked in two places."})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["claim_number"].startswith("CLM-")
    assert body["status"] == "awaiting_photos"  # no photos provided yet


async def test_ticket_create_and_fetch(client):
    r = await client.post("/api/v1/tickets", headers=as_customer(1),
                          json={"subject": "Question about my order", "message": "Where is it?",
                                "category": "shipping"})
    assert r.status_code == 201, r.text
    number = r.json()["ticket_number"]
    r2 = await client.get(f"/api/v1/tickets/{number}", headers=as_customer(1))
    assert r2.status_code == 200
    assert len(r2.json()["messages"]) == 1


async def test_ticket_requires_customer_scope(client):
    r = await client.post("/api/v1/tickets", headers={"X-API-Key": "dev-public-key"},
                          json={"subject": "Hi there", "message": "Hello"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "customer_scope_required"
