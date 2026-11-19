"""Schemas for refunds, returns, claims, cancellations (eligibility + actions)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import Money

# --------------------------- Eligibility (read) ---------------------------


class RefundEligibilityOut(BaseModel):
    order_number: str
    order_value: Money
    refund_verdict: str = Field(
        ..., examples=["eligible_agent_can_approve"],
        description="eligible_agent_can_approve | eligible_needs_human_approval | "
                    "outside_window | blocked_prior_refund | blocked_open_dispute | not_yet_delivered",
    )
    eligible: bool
    within_window: bool
    has_prior_refund: bool
    has_open_dispute: bool
    agent_can_approve: bool
    requires_human_approval: bool
    delivered_at: str | None = None
    days_since_delivery: int | None = None
    policy_id: str
    reason: str


class ReturnItemRuleOut(BaseModel):
    order_item_id: int
    title: str
    category: str
    return_policy_class: str
    is_returnable: bool
    is_final_sale: bool
    hygiene_restricted: bool
    requires_data_wipe: bool
    is_bulky: bool
    restocking_fee_pct: int
    line_total: Money


class ReturnEligibilityOut(BaseModel):
    order_number: str
    eligible: bool
    within_window: bool
    days_since_delivery: int | None = None
    items: list[ReturnItemRuleOut]
    policy_id: str
    reason: str


class CancellationEligibilityOut(BaseModel):
    order_number: str
    status: str
    eligible: bool
    policy_id: str
    reason: str


# --------------------------- Records (read) ---------------------------


class RefundRecordOut(BaseModel):
    refund_id: int
    order_number: str
    amount: Money
    method: str
    status: str
    requires_approval: bool
    approved_by_type: str | None = None
    policy_id: str | None = None
    reason: str | None = None
    created_at: str
    issued_at: str | None = None


class ReturnRecordOut(BaseModel):
    return_id: int
    rma_number: str
    order_number: str
    reason: str
    fault: str
    status: str
    resolution: str | None = None
    return_shipping_payer: str
    restocking_fee: Money
    requested_at: str


class ClaimRecordOut(BaseModel):
    claim_id: int
    claim_number: str
    order_number: str
    type: str
    status: str
    resolution: str | None = None
    photos_provided: bool
    reported_at: str


# --------------------------- Actions (write) ---------------------------


class RefundCreate(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)
    method: str = Field("original_payment", pattern="^(original_payment|store_credit|gift_card)$")
    amount_cents: int | None = Field(
        None, ge=0, description="Defaults to full order value if omitted.")
    customer_confirmed: bool = Field(
        ..., description="Must be true — a refund question is not consent to refund.")


class ReturnCreate(BaseModel):
    reason: str = Field(..., pattern="^(change_of_mind|wrong_size|defective|damaged|"
                                      "wrong_item|missing_item|not_as_described|other)$")
    order_item_ids: list[int] = Field(..., min_length=1)
    customer_confirmed: bool = True


class ClaimCreate(BaseModel):
    type: str = Field(..., pattern="^(damaged|defective|wrong_item|missing_item|missing_part)$")
    order_item_id: int | None = None
    description: str = Field(..., min_length=3, max_length=1000)
    photos_provided: bool = False


class CancellationCreate(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)
    customer_confirmed: bool = True
