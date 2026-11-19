"""Tool API read paths, auth, ownership, pagination, errors."""
from __future__ import annotations

import pytest

from tests.conftest import PUBLIC, as_customer, order_id_for


async def test_health_ok(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["database"] == "up"


async def test_requires_api_key(client):
    r = await client.get("/api/v1/customers/1")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "missing_api_key"


async def test_invalid_api_key(client):
    r = await client.get("/api/v1/customers/1", headers={"X-API-Key": "nope"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "invalid_api_key"


async def test_get_customer(client):
    r = await client.get("/api/v1/customers/1", headers=as_customer(1))
    assert r.status_code == 200
    assert r.json()["email"] == "jordan.lee@example.com"


async def test_ownership_enforced(client):
    oid = await order_id_for(client, 1, "ORD-100001")
    # Customer 2 cannot read customer 1's order.
    r = await client.get(f"/api/v1/orders/{oid}", headers=as_customer(2))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "ownership_violation"


async def test_correlation_id_header(client):
    r = await client.get("/health")
    assert r.headers.get("X-Request-ID")


async def test_orders_pagination(client):
    r = await client.get("/api/v1/customers/1/orders", headers=as_customer(1),
                         params={"limit": 1, "offset": 0})
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["limit"] == 1
    assert len(body["items"]) <= 1
    assert body["meta"]["total"] >= 1


async def test_invalid_sort_rejected(client):
    r = await client.get("/api/v1/customers/1/orders", headers=as_customer(1),
                         params={"sort": "ssn"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("suffix", [
    "", "/status", "/tracking", "/items", "/payment", "/history", "/invoice", "/delivery-estimate",
])
async def test_order_read_endpoints(client, suffix):
    oid = await order_id_for(client, 1, "ORD-100001")
    r = await client.get(f"/api/v1/orders/{oid}{suffix}", headers=as_customer(1))
    assert r.status_code == 200, r.text


async def test_order_not_found(client):
    r = await client.get("/api/v1/orders/999999999", headers=as_customer(1))
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


async def test_payment_never_exposes_full_pan(client):
    oid = await order_id_for(client, 1, "ORD-100001")
    r = await client.get(f"/api/v1/orders/{oid}/payment", headers=as_customer(1))
    assert r.status_code == 200
    for p in r.json():
        if p.get("method_last4") is not None:
            assert len(p["method_last4"]) == 4


async def test_product_catalog(client):
    r = await client.get("/api/v1/products", headers=PUBLIC, params={"limit": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["total"] >= 1
    pid = body["items"][0]["product_id"]
    r2 = await client.get(f"/api/v1/products/{pid}", headers=PUBLIC)
    assert r2.status_code == 200
    assert r2.json()["product_id"] == pid
