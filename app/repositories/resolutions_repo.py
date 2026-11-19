"""Refunds, returns, claims, store credit, cancellations (reads + audited writes)."""
from __future__ import annotations

from typing import Any

from app.repositories.base import Repository


class ResolutionsRepository(Repository):
    async def _next_id(self, table: str, pk: str) -> int:
        val = await self.scalar(f"SELECT COALESCE(MAX({pk}), 0) + 1 FROM {table}")
        return int(val)

    # ------------------------------ Refunds ------------------------------
    async def list_refunds(self, order_id: int) -> list[dict]:
        return await self.fetch_all(
            """
            SELECT r.refund_id, o.order_number, r.amount_cents, r.method, r.status,
                   r.requires_approval, r.approved_by_type, r.policy_id, r.reason,
                   r.created_at, r.issued_at
            FROM refunds r JOIN orders o ON o.order_id = r.order_id
            WHERE r.order_id = :oid ORDER BY r.created_at, r.refund_id
            """,
            {"oid": order_id},
        )

    async def has_refund(self, order_id: int) -> bool:
        return bool(await self.scalar(
            "SELECT 1 FROM refunds WHERE order_id = :oid LIMIT 1", {"oid": order_id}))

    async def insert_refund(self, *, order_id: int, customer_id: int, amount_cents: int,
                            method: str, status: str, requires_approval: bool,
                            approved_by_type: str | None, policy_id: str | None,
                            reason: str) -> int:
        result = await self.execute(
            """
            INSERT INTO refunds(order_id, customer_id, amount_cents, method, status,
                                requires_approval, approved_by_type, policy_id, reason, issued_at)
            VALUES (:order_id, :customer_id, :amount_cents, :method, :status,
                    :requires_approval, :approved_by_type, :policy_id, :reason,
                    CASE WHEN :status = 'issued' THEN datetime('now') END)
            """,
            {
                "order_id": order_id, "customer_id": customer_id, "amount_cents": amount_cents,
                "method": method, "status": status,
                "requires_approval": 1 if requires_approval else 0,
                "approved_by_type": approved_by_type, "policy_id": policy_id, "reason": reason,
            },
        )
        return int(result.lastrowid)

    async def get_refund(self, refund_id: int) -> dict | None:
        return await self.fetch_one(
            """
            SELECT r.refund_id, o.order_number, r.amount_cents, r.method, r.status,
                   r.requires_approval, r.approved_by_type, r.policy_id, r.reason,
                   r.created_at, r.issued_at
            FROM refunds r JOIN orders o ON o.order_id = r.order_id
            WHERE r.refund_id = :rid
            """,
            {"rid": refund_id},
        )

    # ------------------------------ Returns ------------------------------
    async def list_returns(self, order_id: int) -> list[dict]:
        return await self.fetch_all(
            """
            SELECT rt.return_id, rt.rma_number, o.order_number, rt.reason, rt.fault,
                   rt.status, rt.resolution, rt.return_shipping_payer,
                   rt.restocking_fee_cents, rt.requested_at
            FROM returns rt JOIN orders o ON o.order_id = rt.order_id
            WHERE rt.order_id = :oid ORDER BY rt.requested_at, rt.return_id
            """,
            {"oid": order_id},
        )

    async def insert_return(self, *, order_id: int, customer_id: int, reason: str,
                            fault: str, return_shipping_payer: str,
                            restocking_fee_cents: int, order_item_ids: list[int]) -> dict:
        rid = await self._next_id("returns", "return_id")
        rma = f"RMA-{5000 + rid}"
        await self.execute(
            """
            INSERT INTO returns(return_id, rma_number, order_id, customer_id, reason, fault,
                                status, return_shipping_payer, restocking_fee_cents)
            VALUES (:rid, :rma, :order_id, :customer_id, :reason, :fault,
                    'requested', :payer, :fee)
            """,
            {"rid": rid, "rma": rma, "order_id": order_id, "customer_id": customer_id,
             "reason": reason, "fault": fault, "payer": return_shipping_payer,
             "fee": restocking_fee_cents},
        )
        for oi in order_item_ids:
            await self.execute(
                "INSERT INTO return_items(return_id, order_item_id, quantity) "
                "VALUES (:rid, :oi, 1)",
                {"rid": rid, "oi": oi},
            )
        return {"return_id": rid, "rma_number": rma}

    # ------------------------------ Claims ------------------------------
    async def list_claims(self, order_id: int) -> list[dict]:
        return await self.fetch_all(
            """
            SELECT c.claim_id, c.claim_number, o.order_number, c.type, c.status,
                   c.resolution, c.photos_provided, c.reported_at
            FROM claims c JOIN orders o ON o.order_id = c.order_id
            WHERE c.order_id = :oid ORDER BY c.reported_at, c.claim_id
            """,
            {"oid": order_id},
        )

    async def insert_claim(self, *, order_id: int, order_item_id: int | None,
                           customer_id: int, type_: str, photos_provided: bool,
                           description: str) -> dict:
        cid = await self._next_id("claims", "claim_id")
        number = f"CLM-{7000 + cid}"
        status = "open" if photos_provided else "awaiting_photos"
        await self.execute(
            """
            INSERT INTO claims(claim_id, claim_number, order_id, order_item_id, customer_id,
                               type, status, photos_provided, photos_url)
            VALUES (:cid, :num, :order_id, :oi, :customer_id, :type, :status, :photos, :desc)
            """,
            {"cid": cid, "num": number, "order_id": order_id, "oi": order_item_id,
             "customer_id": customer_id, "type": type_, "status": status,
             "photos": 1 if photos_provided else 0, "desc": description[:200]},
        )
        return {"claim_id": cid, "claim_number": number, "status": status}

    # --------------------------- Store credit ---------------------------
    async def insert_store_credit(self, *, customer_id: int, amount_cents: int, reason: str,
                                  source_order_id: int | None, policy_id: str | None) -> int:
        result = await self.execute(
            """
            INSERT INTO store_credits(customer_id, amount_cents, reason, source_order_id, policy_id)
            VALUES (:cid, :amt, :reason, :oid, :pid)
            """,
            {"cid": customer_id, "amt": amount_cents, "reason": reason,
             "oid": source_order_id, "pid": policy_id},
        )
        return int(result.lastrowid)

    # --------------------------- Cancellation ---------------------------
    async def cancel_order(self, order_id: int, reason: str) -> None:
        await self.execute(
            """
            UPDATE orders SET status = 'cancelled', cancelled_at = datetime('now'),
                   cancel_reason = :reason
            WHERE order_id = :oid
            """,
            {"oid": order_id, "reason": reason[:200]},
        )
