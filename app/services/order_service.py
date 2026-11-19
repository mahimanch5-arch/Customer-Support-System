from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.repositories.orders_repo import OrdersRepository
from app.schemas.common import Money
from app.schemas.order import (
    DeliveryEstimateOut,
    InvoiceLineOut,
    InvoiceOut,
    OrderDetailOut,
    OrderItemOut,
    OrderStatusOut,
    OrderSummaryOut,
    PaymentOut,
    StatusHistoryOut,
    TrackingEventOut,
    TrackingOut,
)


def _item(r: dict) -> OrderItemOut:
    return OrderItemOut(
        order_item_id=r["order_item_id"], product_id=r["product_id"], sku=r["sku"],
        title=r["title"], unit_price=Money.of(r["unit_price_cents"]), quantity=r["quantity"],
        line_total=Money.of(r["line_total_cents"]), is_gift=bool(r["is_gift"]),
    )


def _summary(r: dict) -> OrderSummaryOut:
    return OrderSummaryOut(
        order_id=r["order_id"], order_number=r["order_number"], customer_id=r["customer_id"],
        status=r["status"], placed_at=r["placed_at"],
        promised_delivery_date=r["promised_delivery_date"], shipping_method=r["shipping_method"],
        grand_total=Money.of(r["grand_total_cents"]), order_value=Money.of(r["order_value_cents"]),
    )


class OrderService:
    def __init__(self, repo: OrdersRepository) -> None:
        self.repo = repo

    async def list_for_customer(self, customer_id: int, *, limit: int, offset: int,
                                order_by: str, status: str | None) -> tuple[list[OrderSummaryOut], int]:
        rows = await self.repo.list_for_customer(customer_id, limit, offset, order_by, status)
        total = await self.repo.count_for_customer(customer_id, status)
        return [_summary(r) for r in rows], total

    async def get_detail(self, order_id: int) -> OrderDetailOut:
        o = await self.repo.get_detail(order_id)
        if not o:
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        items = [_item(r) for r in await self.repo.get_items(order_id)]
        return OrderDetailOut(
            order_id=o["order_id"], order_number=o["order_number"], customer_id=o["customer_id"],
            status=o["status"], placed_at=o["placed_at"],
            promised_delivery_date=o["promised_delivery_date"],
            shipping_method=o["shipping_method"], channel=o["channel"],
            grand_total=Money.of(o["grand_total_cents"]), order_value=Money.of(o["order_value_cents"]),
            subtotal=Money.of(o["subtotal_cents"]), discount=Money.of(o["discount_cents"]),
            shipping=Money.of(o["shipping_cents"]), tax=Money.of(o["tax_cents"]),
            is_gift=bool(o["is_gift"]), cancelled_at=o["cancelled_at"], items=items,
        )

    async def get_status(self, order_id: int) -> OrderStatusOut:
        o = await self.repo.get_detail(order_id)
        if not o:
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        return OrderStatusOut(order_id=o["order_id"], order_number=o["order_number"],
                              status=o["status"], updated_at=o.get("updated_at"))

    async def get_items(self, order_id: int) -> list[OrderItemOut]:
        if not await self.repo.get_detail(order_id):
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        return [_item(r) for r in await self.repo.get_items(order_id)]

    async def get_tracking(self, order_id: int) -> TrackingOut:
        o = await self.repo.get_detail(order_id)
        if not o:
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        s = await self.repo.get_latest_shipment(order_id)
        if not s:
            return TrackingOut(order_number=o["order_number"], shipment_status=None)
        events = [
            TrackingEventOut(event_time=e["event_time"], status=e["status"],
                             location=e["location"], description=e["description"])
            for e in await self.repo.get_shipment_events(s["shipment_id"])
        ]
        return TrackingOut(
            order_number=o["order_number"], carrier=s["carrier"],
            tracking_number=s["tracking_number"], tracking_url=s["tracking_url"],
            shipment_status=s["status"], estimated_delivery_date=s["estimated_delivery_date"],
            delivered_at=s["delivered_at"], signed_by=s["signed_by"],
            delivery_photo=bool(s["delivery_photo"]), events=events,
        )

    async def get_payments(self, order_id: int) -> list[PaymentOut]:
        if not await self.repo.get_detail(order_id):
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        return [
            PaymentOut(
                payment_id=p["payment_id"], txn_type=p["txn_type"], status=p["status"],
                amount=Money.of(p["amount_cents"]), method_brand=p["method_brand"],
                method_last4=p["method_last4"], processor_ref=p["processor_ref"],
                failure_reason=p["failure_reason"], created_at=p["created_at"],
            )
            for p in await self.repo.get_payments(order_id)
        ]

    async def get_history(self, order_id: int) -> list[StatusHistoryOut]:
        if not await self.repo.get_detail(order_id):
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        return [StatusHistoryOut(status=h["status"], note=h["note"], changed_at=h["changed_at"])
                for h in await self.repo.get_status_history(order_id)]

    async def get_invoice(self, order_id: int) -> InvoiceOut:
        detail = await self.get_detail(order_id)
        c = await self.repo.get_detail(order_id)  # already validated
        lines = [
            InvoiceLineOut(title=i.title, quantity=i.quantity,
                           unit_price=i.unit_price, line_total=i.line_total)
            for i in detail.items
        ]
        bill_to = f"Customer #{c['customer_id']}"
        return InvoiceOut(
            order_number=detail.order_number, placed_at=detail.placed_at, bill_to=bill_to,
            lines=lines, subtotal=detail.subtotal, discount=detail.discount,
            shipping=detail.shipping, tax=detail.tax, grand_total=detail.grand_total,
        )

    async def get_delivery_estimate(self, order_id: int) -> DeliveryEstimateOut:
        o = await self.repo.get_detail(order_id)
        if not o:
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        s = await self.repo.get_latest_shipment(order_id)
        dstat = await self.repo.delivery_status(order_id)
        days_late = dstat.get("days_late") if dstat else None
        delivered_at = s["delivered_at"] if s else None
        if delivered_at:
            msg = f"Delivered on {delivered_at}."
            if days_late and days_late > 0:
                msg += f" ({days_late} day(s) later than promised.)"
        elif s and s["estimated_delivery_date"]:
            msg = f"Estimated delivery {s['estimated_delivery_date']} (status: {o['status']})."
        elif o["promised_delivery_date"]:
            msg = f"Promised by {o['promised_delivery_date']} (status: {o['status']})."
        else:
            msg = f"No delivery estimate available yet (status: {o['status']})."
        return DeliveryEstimateOut(
            order_number=o["order_number"], status=o["status"],
            promised_delivery_date=o["promised_delivery_date"],
            estimated_delivery_date=s["estimated_delivery_date"] if s else None,
            delivered_at=delivered_at, days_late=days_late, message=msg,
        )
