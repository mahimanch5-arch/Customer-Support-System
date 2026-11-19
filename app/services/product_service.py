from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.repositories.products_repo import ProductsRepository
from app.schemas.common import Money
from app.schemas.product import ProductOut


def _out(r: dict) -> ProductOut:
    return ProductOut(
        product_id=r["product_id"], sku=r["sku"], title=r["title"], description=r["description"],
        category=r["category"], brand=r["brand"], price=Money.of(r["price_cents"]),
        stock_quantity=r["stock_quantity"], is_returnable=bool(r["is_returnable"]),
        is_final_sale=bool(r["is_final_sale"]), hygiene_restricted=bool(r["hygiene_restricted"]),
        requires_data_wipe=bool(r["requires_data_wipe"]), warranty_months=r["warranty_months"],
        warranty_type=r["warranty_type"], lifecycle_status=r["lifecycle_status"],
        restock_eta=r["restock_eta"],
    )


class ProductService:
    def __init__(self, repo: ProductsRepository) -> None:
        self.repo = repo

    async def get(self, product_id: int) -> ProductOut:
        r = await self.repo.get(product_id)
        if not r:
            raise NotFoundError("Product not found.", details={"product_id": product_id})
        return _out(r)

    async def search(self, q: str | None, category: str | None,
                     limit: int, offset: int) -> tuple[list[ProductOut], int]:
        rows = await self.repo.search(q, category, limit, offset)
        total = await self.repo.count(q, category)
        return [_out(r) for r in rows], total
