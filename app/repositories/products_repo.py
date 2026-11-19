from __future__ import annotations

from app.repositories.base import Repository


class ProductsRepository(Repository):
    async def get(self, product_id: int) -> dict | None:
        return await self.fetch_one(
            """
            SELECT p.product_id, p.sku, p.title, p.description, c.slug AS category,
                   p.brand, p.price_cents, p.stock_quantity, p.is_returnable, p.is_final_sale,
                   p.hygiene_restricted, p.requires_data_wipe, p.warranty_months,
                   p.warranty_type, p.lifecycle_status, p.restock_eta
            FROM products p JOIN categories c ON c.category_id = p.category_id
            WHERE p.product_id = :pid
            """,
            {"pid": product_id},
        )

    async def search(self, q: str | None, category: str | None,
                     limit: int, offset: int) -> list[dict]:
        where = "WHERE 1=1"
        params: dict = {"limit": limit, "offset": offset}
        if q:
            where += " AND (p.title LIKE :q OR p.description LIKE :q)"
            params["q"] = f"%{q}%"
        if category:
            where += " AND c.slug = :cat"
            params["cat"] = category
        return await self.fetch_all(
            f"""
            SELECT p.product_id, p.sku, p.title, p.description, c.slug AS category,
                   p.brand, p.price_cents, p.stock_quantity, p.is_returnable, p.is_final_sale,
                   p.hygiene_restricted, p.requires_data_wipe, p.warranty_months,
                   p.warranty_type, p.lifecycle_status, p.restock_eta
            FROM products p JOIN categories c ON c.category_id = p.category_id
            {where} ORDER BY p.title LIMIT :limit OFFSET :offset
            """,
            params,
        )

    async def count(self, q: str | None, category: str | None) -> int:
        where = "WHERE 1=1"
        params: dict = {}
        if q:
            where += " AND (p.title LIKE :q OR p.description LIKE :q)"
            params["q"] = f"%{q}%"
        if category:
            where += " AND c.slug = :cat"
            params["cat"] = category
        return int(await self.scalar(
            f"SELECT COUNT(*) FROM products p JOIN categories c ON c.category_id = p.category_id {where}",
            params,
        ) or 0)
