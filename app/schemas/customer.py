from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import Money


class CustomerOut(BaseModel):
    customer_id: int
    email: str
    first_name: str
    last_name: str
    phone: str | None = None
    loyalty_tier: str
    status: str
    marketing_opt_in: bool
    created_at: str


class AddressOut(BaseModel):
    address_id: int
    label: str | None = None
    recipient_name: str
    line1: str
    line2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str
    is_default_shipping: bool
    is_default_billing: bool


class StoreCreditOut(BaseModel):
    customer_id: int
    balance: Money
