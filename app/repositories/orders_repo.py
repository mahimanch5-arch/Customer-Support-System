from __future__ import annotations

from app.repositories.base import Repository


class OrdersRepository(Repository):
    # ---- identity / ownership ----
    async def get_owner(self, order_id: int) -> dict | None:
        return await self.fetch_one(
            "SELECT order_id, order_number, customer_id, status FROM orders WHERE order_id = :oid",
            {"oid": order_id},
        )

    # ---- lists / summaries ----
    async def list_for_customer(
        self, customer_id: int, limit: int, offset: int, order_by: str,
        status: str | None = None,
    ) -> list[dict]:
        where = "WHERE customer_id = :cid"
        params: dict = {"cid": customer_id, "limit": limit, "offset": offset}
        if status:
            where += " AND status = :status"
            params["status"] = status
        return await self.fetch_all(
            f"""
            SELECT order_id, order_number, customer_id, status, placed_at,
                   promised_delivery_date, shipping_method, grand_total_cents,
                   order_value_cents, currency
            FROM orders {where}
            ORDER BY {order_by}
            LIMIT :limit OFFSET :offset
            """,
            params,
        )

    async def count_for_customer(self, customer_id: int, status: str | None = None) -> int:
        where = "WHERE customer_id = :cid"
        params: dict = {"cid": customer_id}
        if status:
            where += " AND status = :status"
            params["status"] = status
        return int(await self.scalar(f"SELECT COUNT(*) FROM orders {where}", params) or 0)

    async def get_detail(self, order_id: int) -> dict | None:
        return await self.fetch_one(
            """
            SELECT order_id, order_number, customer_id, status, placed_at,
                   promised_delivery_date, shipping_method, channel, currency,
                   subtotal_cents, discount_cents, shipping_cents, tax_cents,
                   grand_total_cents, order_value_cents, is_gift, cancelled_at, updated_at
            FROM orders WHERE order_id = :oid
            """,
            {"oid": order_id},
        )

    async def get_items(self, order_id: int) -> list[dict]:
        return await self.fetch_all(
            """
            SELECT order_item_id, product_id, sku, title, unit_price_cents,
                   quantity, line_total_cents, is_gift
            FROM order_items WHERE order_id = :oid ORDER BY order_item_id
            """,
            {"oid": order_id},
        )

    async def get_status_history(self, order_id: int) -> list[dict]:
        return await self.fetch_all(
            """
            SELECT status, note, changed_at FROM order_status_history
            WHERE order_id = :oid ORDER BY changed_at, history_id
            """,
            {"oid": order_id},
        )

    # ---- fulfillment ----
    async def get_latest_shipment(self, order_id: int) -> dict | None:
        return await self.fetch_one(
            """
            SELECT shipment_id, carrier, tracking_number, tracking_url, status,
                   shipped_at, estimated_delivery_date, delivered_at, signed_by, delivery_photo
            FROM shipments WHERE order_id = :oid
            ORDER BY created_at DESC LIMIT 1
            """,
            {"oid": order_id},
        )

    async def get_shipment_events(self, shipment_id: int) -> list[dict]:
        return await self.fetch_all(
            """
            SELECT event_time, status, location, description FROM shipment_events
            WHERE shipment_id = :sid ORDER BY event_time
            """,
            {"sid": shipment_id},
        )

    # ---- payments ----
    async def get_payments(self, order_id: int) -> list[dict]:
        return await self.fetch_all(
            """
            SELECT p.payment_id, p.txn_type, p.status, p.amount_cents,
                   p.processor_ref, p.failure_reason, p.created_at,
                   pm.brand AS method_brand, pm.last4 AS method_last4
            FROM payments p
            LEFT JOIN payment_methods pm ON pm.payment_method_id = p.payment_method_id
            WHERE p.order_id = :oid ORDER BY p.created_at, p.payment_id
            """,
            {"oid": order_id},
        )

    # ---- policy views ----
    async def refund_eligibility(self, order_id: int) -> dict | None:
        return await self.fetch_one(
            "SELECT * FROM v_refund_eligibility WHERE order_id = :oid", {"oid": order_id})

    async def delivery_status(self, order_id: int) -> dict | None:
        return await self.fetch_one(
            "SELECT * FROM v_delivery_status WHERE order_id = :oid", {"oid": order_id})

    async def return_item_rules(self, order_id: int) -> list[dict]:
        return await self.fetch_all(
            "SELECT * FROM v_order_item_return_rules WHERE order_id = :oid", {"oid": order_id})

    async def order_summary(self, order_id: int) -> dict | None:
        return await self.fetch_one(
            "SELECT * FROM v_order_summary WHERE order_id = :oid", {"oid": order_id})
