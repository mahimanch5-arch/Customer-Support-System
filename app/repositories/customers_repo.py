from __future__ import annotations

from app.repositories.base import Repository


class CustomersRepository(Repository):
    async def get(self, customer_id: int) -> dict | None:
        return await self.fetch_one(
            """
            SELECT customer_id, email, first_name, last_name, phone,
                   marketing_opt_in, loyalty_tier, status, created_at
            FROM customers WHERE customer_id = :cid
            """,
            {"cid": customer_id},
        )

    async def get_by_email(self, email: str) -> dict | None:
        return await self.fetch_one(
            "SELECT customer_id, email FROM customers WHERE email = :email",
            {"email": email},
        )

    async def list_addresses(self, customer_id: int) -> list[dict]:
        return await self.fetch_all(
            """
            SELECT address_id, label, recipient_name, line1, line2, city, state,
                   postal_code, country, is_default_shipping, is_default_billing
            FROM addresses WHERE customer_id = :cid
            ORDER BY is_default_shipping DESC, address_id
            """,
            {"cid": customer_id},
        )

    async def store_credit_balance(self, customer_id: int) -> int:
        val = await self.scalar(
            "SELECT balance_cents FROM v_store_credit_balance WHERE customer_id = :cid",
            {"cid": customer_id},
        )
        return int(val or 0)
