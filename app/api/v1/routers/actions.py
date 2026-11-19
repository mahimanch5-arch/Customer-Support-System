"""Order write Tool APIs: refunds, returns, claims, cancellation, goodwill.

All mutate data, so they are POST (never GET), are idempotent via the optional
`Idempotency-Key` header, and enforce business rules + confirmation server-side.
"""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from fastapi.encoders import jsonable_encoder

from app.api.deps import CurrentPrincipal, OwnedOrder, ResolutionSvc, get_idempotency_key
from app.services import idempotency
from app.schemas.resolution import (
    CancellationCreate,
    ClaimCreate,
    RefundCreate,
    ReturnCreate,
)

router = APIRouter(prefix="/orders", tags=["order-actions"])

IdemKey = Annotated[str | None, Depends(get_idempotency_key)]


async def _idempotent(principal, scope: str, key: str | None, order_id: int, produce):
    """Replay a prior result for the same Idempotency-Key, else run and store it."""
    if key:
        cached = idempotency.get(principal.name, f"{scope}:{order_id}", key)
        if cached is not None:
            return cached
    result = jsonable_encoder(await produce())
    if key:
        idempotency.put(principal.name, f"{scope}:{order_id}", key, result)
    return result


@router.post("/{order_id}/refunds", status_code=status.HTTP_201_CREATED,
             summary="Initiate a refund (requires confirmation; >$100 escalates)")
async def create_refund(order: OwnedOrder, body: RefundCreate, svc: ResolutionSvc,
                        principal: CurrentPrincipal, idem: IdemKey) -> Any:
    return await _idempotent(
        principal, "refund", idem, order["order_id"],
        lambda: svc.initiate_refund(order["order_id"], reason=body.reason, method=body.method,
                                    amount_cents=body.amount_cents,
                                    customer_confirmed=body.customer_confirmed),
    )


@router.post("/{order_id}/returns", status_code=status.HTTP_201_CREATED,
             summary="Create a return (RMA)")
async def create_return(order: OwnedOrder, body: ReturnCreate, svc: ResolutionSvc,
                        principal: CurrentPrincipal, idem: IdemKey) -> Any:
    return await _idempotent(
        principal, "return", idem, order["order_id"],
        lambda: svc.create_return(order["order_id"], reason=body.reason,
                                  order_item_ids=body.order_item_ids),
    )


@router.post("/{order_id}/claims", status_code=status.HTTP_201_CREATED,
             summary="Open a damage/wrong/missing-item claim")
async def create_claim(order: OwnedOrder, body: ClaimCreate, svc: ResolutionSvc,
                       principal: CurrentPrincipal, idem: IdemKey) -> Any:
    return await _idempotent(
        principal, "claim", idem, order["order_id"],
        lambda: svc.create_claim(order["order_id"], type_=body.type,
                                 order_item_id=body.order_item_id, description=body.description,
                                 photos_provided=body.photos_provided),
    )


@router.post("/{order_id}/cancel", summary="Cancel an unshipped order (requires confirmation)")
async def cancel_order(order: OwnedOrder, body: CancellationCreate, svc: ResolutionSvc,
                       principal: CurrentPrincipal, idem: IdemKey) -> Any:
    return await _idempotent(
        principal, "cancel", idem, order["order_id"],
        lambda: svc.cancel_order(order["order_id"], reason=body.reason,
                                 customer_confirmed=body.customer_confirmed),
    )


@router.post("/{order_id}/goodwill-credit", status_code=status.HTTP_201_CREATED,
             summary="Grant the policy delay goodwill credit ($0/$5/$15, max one/order)")
async def goodwill_credit(order: OwnedOrder, svc: ResolutionSvc,
                          principal: CurrentPrincipal, idem: IdemKey) -> Any:
    return await _idempotent(
        principal, "goodwill", idem, order["order_id"],
        lambda: svc.issue_delay_goodwill(order["order_id"]),
    )
