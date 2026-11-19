"""Customer Tool APIs."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CustomerAccess, CustomerSvc, OrderSvc
from app.core.pagination import PageParams, page_params, resolve_sort
from app.schemas.common import Page, make_page
from app.schemas.customer import AddressOut, CustomerOut, StoreCreditOut
from app.schemas.order import OrderSummaryOut

router = APIRouter(prefix="/customers", tags=["customers"])

_ORDER_SORTS = {"placed_at": "placed_at", "total": "grand_total_cents", "status": "status"}


@router.get("/{customer_id}", response_model=CustomerOut, summary="Retrieve customer details")
async def get_customer(customer_id: CustomerAccess, svc: CustomerSvc) -> CustomerOut:
    return await svc.get_customer(customer_id)


@router.get("/{customer_id}/orders", response_model=Page[OrderSummaryOut],
            summary="Retrieve all orders for a customer")
async def get_customer_orders(
    customer_id: CustomerAccess,
    svc: OrderSvc,
    page: Annotated[PageParams, Depends(page_params)],
    status: Annotated[str | None, Query(description="Filter by order status")] = None,
) -> Page[OrderSummaryOut]:
    order_by = resolve_sort(page, _ORDER_SORTS, "placed_at DESC, order_id DESC")
    items, total = await svc.list_for_customer(
        customer_id, limit=page.limit, offset=page.offset, order_by=order_by, status=status)
    return make_page(items, total, page.limit, page.offset)


@router.get("/{customer_id}/addresses", response_model=list[AddressOut],
            summary="Retrieve saved customer addresses")
async def get_customer_addresses(customer_id: CustomerAccess, svc: CustomerSvc) -> list[AddressOut]:
    return await svc.list_addresses(customer_id)


@router.get("/{customer_id}/store-credit", response_model=StoreCreditOut,
            summary="Retrieve customer store-credit balance")
async def get_customer_store_credit(customer_id: CustomerAccess, svc: CustomerSvc) -> StoreCreditOut:
    return await svc.store_credit(customer_id)
