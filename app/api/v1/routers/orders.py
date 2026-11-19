"""Order Tool APIs — all read-only (GET). Writes live in actions.py."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import OrderSvc, OwnedOrder, ResolutionSvc
from app.schemas.order import (
    DeliveryEstimateOut,
    InvoiceOut,
    OrderDetailOut,
    OrderItemOut,
    OrderStatusOut,
    PaymentOut,
    StatusHistoryOut,
    TrackingOut,
)
from app.schemas.resolution import (
    CancellationEligibilityOut,
    ClaimRecordOut,
    RefundEligibilityOut,
    RefundRecordOut,
    ReturnEligibilityOut,
    ReturnRecordOut,
)

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/{order_id}", response_model=OrderDetailOut, summary="Retrieve complete order details")
async def get_order(order: OwnedOrder, svc: OrderSvc) -> OrderDetailOut:
    return await svc.get_detail(order["order_id"])


@router.get("/{order_id}/status", response_model=OrderStatusOut, summary="Retrieve current order status")
async def get_order_status(order: OwnedOrder, svc: OrderSvc) -> OrderStatusOut:
    return await svc.get_status(order["order_id"])


@router.get("/{order_id}/tracking", response_model=TrackingOut, summary="Retrieve shipment & tracking")
async def get_order_tracking(order: OwnedOrder, svc: OrderSvc) -> TrackingOut:
    return await svc.get_tracking(order["order_id"])


@router.get("/{order_id}/items", response_model=list[OrderItemOut], summary="Retrieve order items")
async def get_order_items(order: OwnedOrder, svc: OrderSvc) -> list[OrderItemOut]:
    return await svc.get_items(order["order_id"])


@router.get("/{order_id}/payment", response_model=list[PaymentOut], summary="Retrieve payment information")
async def get_order_payment(order: OwnedOrder, svc: OrderSvc) -> list[PaymentOut]:
    return await svc.get_payments(order["order_id"])


@router.get("/{order_id}/history", response_model=list[StatusHistoryOut], summary="Retrieve status history")
async def get_order_history(order: OwnedOrder, svc: OrderSvc) -> list[StatusHistoryOut]:
    return await svc.get_history(order["order_id"])


@router.get("/{order_id}/invoice", response_model=InvoiceOut, summary="Retrieve order invoice")
async def get_order_invoice(order: OwnedOrder, svc: OrderSvc) -> InvoiceOut:
    return await svc.get_invoice(order["order_id"])


@router.get("/{order_id}/delivery-estimate", response_model=DeliveryEstimateOut,
            summary="Retrieve delivery estimate")
async def get_delivery_estimate(order: OwnedOrder, svc: OrderSvc) -> DeliveryEstimateOut:
    return await svc.get_delivery_estimate(order["order_id"])


# ---- eligibility (read-only policy evaluations) ----
@router.get("/{order_id}/refund-eligibility", response_model=RefundEligibilityOut,
            summary="Check refund eligibility (does NOT issue a refund)")
async def refund_eligibility(order: OwnedOrder, svc: ResolutionSvc) -> RefundEligibilityOut:
    return await svc.refund_eligibility(order["order_id"])


@router.get("/{order_id}/return-eligibility", response_model=ReturnEligibilityOut,
            summary="Check return eligibility")
async def return_eligibility(order: OwnedOrder, svc: ResolutionSvc) -> ReturnEligibilityOut:
    return await svc.return_eligibility(order["order_id"])


@router.get("/{order_id}/cancellation-eligibility", response_model=CancellationEligibilityOut,
            summary="Check cancellation eligibility")
async def cancellation_eligibility(order: OwnedOrder, svc: ResolutionSvc) -> CancellationEligibilityOut:
    return await svc.cancellation_eligibility(order["order_id"])


# ---- existing records ----
@router.get("/{order_id}/refunds", response_model=list[RefundRecordOut], summary="Retrieve refund records")
async def get_refunds(order: OwnedOrder, svc: ResolutionSvc) -> list[RefundRecordOut]:
    return await svc.list_refunds(order["order_id"])


@router.get("/{order_id}/returns", response_model=list[ReturnRecordOut], summary="Retrieve return records")
async def get_returns(order: OwnedOrder, svc: ResolutionSvc) -> list[ReturnRecordOut]:
    return await svc.list_returns(order["order_id"])


@router.get("/{order_id}/claims", response_model=list[ClaimRecordOut], summary="Retrieve claim records")
async def get_claims(order: OwnedOrder, svc: ResolutionSvc) -> list[ClaimRecordOut]:
    return await svc.list_claims(order["order_id"])
