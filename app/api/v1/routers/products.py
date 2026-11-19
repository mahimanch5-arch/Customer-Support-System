"""Product catalog Tool APIs (read-only)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import ProductSvc, get_principal
from app.core.pagination import PageParams, page_params
from app.schemas.common import Page, make_page
from app.schemas.product import ProductOut

router = APIRouter(prefix="/products", tags=["products"], dependencies=[Depends(get_principal)])


@router.get("", response_model=Page[ProductOut], summary="Search / list products")
async def list_products(
    svc: ProductSvc,
    page: Annotated[PageParams, Depends(page_params)],
    q: Annotated[str | None, Query(description="Full-text match on title/description")] = None,
    category: Annotated[str | None, Query(description="Category slug filter")] = None,
) -> Page[ProductOut]:
    items, total = await svc.search(q, category, page.limit, page.offset)
    return make_page(items, total, page.limit, page.offset)


@router.get("/{product_id}", response_model=ProductOut, summary="Retrieve product details")
async def get_product(product_id: int, svc: ProductSvc) -> ProductOut:
    return await svc.get(product_id)
