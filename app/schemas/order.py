from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import Money


class OrderSummaryOut(BaseModel):
    order_id: int
    order_number: str
    customer_id: int
    status: str
    placed_at: str
    promised_delivery_date: str | None = None
    shipping_method: str
    grand_total: Money
    order_value: Money  # subtotal - discount; drives the $100 threshold


class OrderItemOut(BaseModel):
    order_item_id: int
    product_id: int
    sku: str
    title: str
    unit_price: Money
    quantity: int
    line_total: Money
    is_gift: bool


class OrderDetailOut(OrderSummaryOut):
    subtotal: Money
    discount: Money
    shipping: Money
    tax: Money
    is_gift: bool
    channel: str
    cancelled_at: str | None = None
    items: list[OrderItemOut] = []


class OrderStatusOut(BaseModel):
    order_id: int
    order_number: str
    status: str
    updated_at: str | None = None


class TrackingOut(BaseModel):
    order_number: str
    carrier: str | None = None
    tracking_number: str | None = None
    tracking_url: str | None = None
    shipment_status: str | None = None
    estimated_delivery_date: str | None = None
    delivered_at: str | None = None
    signed_by: str | None = None
    delivery_photo: bool = False
    events: list["TrackingEventOut"] = []


class TrackingEventOut(BaseModel):
    event_time: str
    status: str
    location: str | None = None
    description: str


class PaymentOut(BaseModel):
    payment_id: int
    txn_type: str
    status: str
    amount: Money
    method_brand: str | None = None
    method_last4: str | None = None  # last4 only; full PAN never stored
    processor_ref: str | None = None
    failure_reason: str | None = None
    created_at: str


class StatusHistoryOut(BaseModel):
    status: str
    note: str | None = None
    changed_at: str


class InvoiceLineOut(BaseModel):
    title: str
    quantity: int
    unit_price: Money
    line_total: Money


class InvoiceOut(BaseModel):
    order_number: str
    placed_at: str
    bill_to: str
    lines: list[InvoiceLineOut]
    subtotal: Money
    discount: Money
    shipping: Money
    tax: Money
    grand_total: Money


class DeliveryEstimateOut(BaseModel):
    order_number: str
    status: str
    promised_delivery_date: str | None = None
    estimated_delivery_date: str | None = None
    delivered_at: str | None = None
    days_late: int | None = None
    message: str


TrackingOut.model_rebuild()
