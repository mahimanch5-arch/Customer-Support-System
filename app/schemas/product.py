from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import Money


class ProductOut(BaseModel):
    product_id: int
    sku: str
    title: str
    description: str | None = None
    category: str
    brand: str | None = None
    price: Money
    stock_quantity: int
    is_returnable: bool
    is_final_sale: bool
    hygiene_restricted: bool
    requires_data_wipe: bool
    warranty_months: int
    warranty_type: str | None = None
    lifecycle_status: str
    restock_eta: str | None = None
