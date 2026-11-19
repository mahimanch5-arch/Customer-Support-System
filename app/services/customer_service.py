from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.repositories.customers_repo import CustomersRepository
from app.schemas.common import Money
from app.schemas.customer import AddressOut, CustomerOut, StoreCreditOut


class CustomerService:
    def __init__(self, repo: CustomersRepository) -> None:
        self.repo = repo

    async def get_customer(self, customer_id: int) -> CustomerOut:
        row = await self.repo.get(customer_id)
        if not row:
            raise NotFoundError("Customer not found.", details={"customer_id": customer_id})
        return CustomerOut(
            customer_id=row["customer_id"], email=row["email"],
            first_name=row["first_name"], last_name=row["last_name"], phone=row["phone"],
            loyalty_tier=row["loyalty_tier"], status=row["status"],
            marketing_opt_in=bool(row["marketing_opt_in"]), created_at=row["created_at"],
        )

    async def list_addresses(self, customer_id: int) -> list[AddressOut]:
        await self.get_customer(customer_id)  # existence + ownership upstream
        rows = await self.repo.list_addresses(customer_id)
        return [
            AddressOut(
                address_id=r["address_id"], label=r["label"], recipient_name=r["recipient_name"],
                line1=r["line1"], line2=r["line2"], city=r["city"], state=r["state"],
                postal_code=r["postal_code"], country=r["country"],
                is_default_shipping=bool(r["is_default_shipping"]),
                is_default_billing=bool(r["is_default_billing"]),
            )
            for r in rows
        ]

    async def store_credit(self, customer_id: int) -> StoreCreditOut:
        await self.get_customer(customer_id)
        bal = await self.repo.store_credit_balance(customer_id)
        return StoreCreditOut(customer_id=customer_id, balance=Money.of(bal))
