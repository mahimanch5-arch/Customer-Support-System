"""Refund / return / cancellation / claim / goodwill logic.

This is where the KB's fixed business rules are enforced against the DB policy
views so the API and the knowledge base never disagree:
  * 30-day refund window, one refund per order, open-dispute block  -> v_refund_eligibility
  * $100 agent approval limit (over -> human approval queue)         -> order_value / verdict
  * delay goodwill tiers $0/$5/$15, max one per order                -> v_delivery_status
A refund QUESTION is never consent: writes require `customer_confirmed=True`.
"""
from __future__ import annotations

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.core.logging import get_logger
from app.repositories.orders_repo import OrdersRepository
from app.repositories.resolutions_repo import ResolutionsRepository
from app.repositories.support_repo import SupportRepository
from app.schemas.common import Money
from app.schemas.resolution import (
    CancellationEligibilityOut,
    ClaimRecordOut,
    RefundEligibilityOut,
    RefundRecordOut,
    ReturnEligibilityOut,
    ReturnItemRuleOut,
    ReturnRecordOut,
)

logger = get_logger("app.resolution")

# verdict -> (policy_id, human-readable reason)
_VERDICT = {
    "eligible_agent_can_approve": ("REF-001", "Within the 30-day window and within the agent's $100 approval limit."),
    "eligible_needs_human_approval": ("REF-002", "Within the window, but order value exceeds $100 — requires human approval."),
    "outside_window": ("REF-001", "Outside the 30-day refund window (measured from delivery)."),
    "blocked_prior_refund": ("REF-003", "A refund has already been issued for this order (one refund per order)."),
    "blocked_open_dispute": ("PAY-004", "An open payment dispute/chargeback exists — the store must not also issue a refund."),
    "not_yet_delivered": ("REF-001", "The order has not been delivered yet; the refund window starts at delivery."),
}
_ELIGIBLE = {"eligible_agent_can_approve", "eligible_needs_human_approval"}
_NON_RETURNABLE_CLASS_NOTE = "Final-sale / hygiene / perishable items are non-returnable once opened."


class ResolutionService:
    def __init__(self, orders: OrdersRepository, resolutions: ResolutionsRepository,
                 support: SupportRepository, approval_limit_cents: int = 10000) -> None:
        self.orders = orders
        self.resolutions = resolutions
        self.support = support
        self.limit = approval_limit_cents

    # ------------------------------ Reads ------------------------------
    async def refund_eligibility(self, order_id: int) -> RefundEligibilityOut:
        v = await self.orders.refund_eligibility(order_id)
        if not v:
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        verdict = v["refund_verdict"]
        policy_id, reason = _VERDICT.get(verdict, ("REF-001", "See refund policy."))
        return RefundEligibilityOut(
            order_number=v["order_number"], order_value=Money.of(v["order_value_cents"]),
            refund_verdict=verdict, eligible=verdict in _ELIGIBLE,
            within_window=bool(v["within_window"]), has_prior_refund=bool(v["has_prior_refund"]),
            has_open_dispute=bool(v["has_open_dispute"]), agent_can_approve=bool(v["agent_can_approve"]),
            requires_human_approval=(verdict == "eligible_needs_human_approval"),
            delivered_at=v["delivered_at"], days_since_delivery=v["days_since_delivery"],
            policy_id=policy_id, reason=reason,
        )

    async def return_eligibility(self, order_id: int) -> ReturnEligibilityOut:
        rules = await self.orders.return_item_rules(order_id)
        if not rules:
            raise NotFoundError("Order not found or has no items.", details={"order_id": order_id})
        dstat = await self.orders.delivery_status(order_id)
        days = dstat.get("days_since_delivery") if dstat else None
        within = days is not None and days <= 30
        order_number = rules[0]["order_number"]
        items = [
            ReturnItemRuleOut(
                order_item_id=r["order_item_id"], title=r["title"], category=r["category"],
                return_policy_class=r["return_policy_class"], is_returnable=bool(r["is_returnable"]),
                is_final_sale=bool(r["is_final_sale"]), hygiene_restricted=bool(r["hygiene_restricted"]),
                requires_data_wipe=bool(r["requires_data_wipe"]), is_bulky=bool(r["is_bulky"]),
                restocking_fee_pct=r["restocking_fee_pct"], line_total=Money.of(r["line_total_cents"]),
            )
            for r in rules
        ]
        any_returnable = any(i.is_returnable and not i.is_final_sale for i in items)
        eligible = within and any_returnable
        if not within:
            reason = "Outside the 30-day return window (measured from delivery)."
        elif not any_returnable:
            reason = _NON_RETURNABLE_CLASS_NOTE
        else:
            reason = "Within the return window; at least one item is returnable (restocking fees may apply)."
        return ReturnEligibilityOut(
            order_number=order_number, eligible=eligible, within_window=within,
            days_since_delivery=days, items=items, policy_id="RET-001", reason=reason,
        )

    async def cancellation_eligibility(self, order_id: int) -> CancellationEligibilityOut:
        o = await self.orders.get_detail(order_id)
        if not o:
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        cancelable = o["status"] in ("pending", "processing")
        if o["status"] in ("cancelled",):
            reason = "Order is already cancelled."
        elif cancelable:
            reason = "Order has not shipped yet and can be cancelled."
        else:
            reason = ("Order has already shipped. Once shipped it cannot be cancelled; "
                      "a return or refusal of delivery is required (ORD-002).")
        return CancellationEligibilityOut(
            order_number=o["order_number"], status=o["status"], eligible=cancelable,
            policy_id="ORD-002", reason=reason,
        )

    async def list_refunds(self, order_id: int) -> list[RefundRecordOut]:
        if not await self.orders.get_owner(order_id):
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        return [self._refund_out(r) for r in await self.resolutions.list_refunds(order_id)]

    async def list_returns(self, order_id: int) -> list[ReturnRecordOut]:
        if not await self.orders.get_owner(order_id):
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        return [
            ReturnRecordOut(
                return_id=r["return_id"], rma_number=r["rma_number"], order_number=r["order_number"],
                reason=r["reason"], fault=r["fault"], status=r["status"], resolution=r["resolution"],
                return_shipping_payer=r["return_shipping_payer"],
                restocking_fee=Money.of(r["restocking_fee_cents"]), requested_at=r["requested_at"],
            )
            for r in await self.resolutions.list_returns(order_id)
        ]

    async def list_claims(self, order_id: int) -> list[ClaimRecordOut]:
        if not await self.orders.get_owner(order_id):
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        return [
            ClaimRecordOut(
                claim_id=c["claim_id"], claim_number=c["claim_number"], order_number=c["order_number"],
                type=c["type"], status=c["status"], resolution=c["resolution"],
                photos_provided=bool(c["photos_provided"]), reported_at=c["reported_at"],
            )
            for c in await self.resolutions.list_claims(order_id)
        ]

    # ------------------------------ Writes ------------------------------
    async def initiate_refund(self, order_id: int, *, reason: str, method: str,
                              amount_cents: int | None, customer_confirmed: bool) -> dict:
        """Returns {"status": "issued"|"pending_approval", "refund": RefundRecordOut, "message": str}."""
        if not customer_confirmed:
            raise BusinessRuleError(
                "A refund requires explicit customer confirmation. A refund question is not consent.",
                code="confirmation_required",
            )
        v = await self.orders.refund_eligibility(order_id)
        if not v:
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        verdict = v["refund_verdict"]
        policy_id, verdict_reason = _VERDICT.get(verdict, ("REF-001", "See refund policy."))

        if verdict not in _ELIGIBLE:
            raise BusinessRuleError(
                f"Refund declined: {verdict_reason}",
                code=f"refund_{verdict}", details={"verdict": verdict, "policy_id": policy_id},
            )

        order_value = int(v["order_value_cents"])
        amount = amount_cents if amount_cents is not None else order_value
        if amount <= 0 or amount > order_value:
            raise BusinessRuleError(
                "Refund amount must be positive and not exceed the order value.",
                code="invalid_amount",
                details={"requested_cents": amount, "order_value_cents": order_value},
            )

        needs_human = verdict == "eligible_needs_human_approval" or amount > self.limit

        if needs_human:
            # Do NOT issue. Queue for human approval and open a ticket (REF-002).
            ticket = await self.support.create_ticket(
                customer_id=v["customer_id"], order_id=order_id, channel="chat",
                category="refunds", subject=f"Refund approval — {v['order_number']}",
                priority="high", escalated=True,
                escalation_reason="refund over $100 requires human approval (REF-002)",
                assigned_to="human", sentiment=None, policy_id_cited="REF-002",
            )
            refund_id = await self.resolutions.insert_refund(
                order_id=order_id, customer_id=v["customer_id"], amount_cents=amount,
                method=method, status="pending", requires_approval=True,
                approved_by_type=None, policy_id="REF-002", reason=reason,
            )
            await self.support.create_approval(
                ticket_id=ticket["ticket_id"], action_id=None,
                reason=f"Refund {Money.of(amount).display} > $100 (REF-002)", amount_cents=amount,
            )
            rec = await self.resolutions.get_refund(refund_id)
            return {
                "status": "pending_approval",
                "refund": self._refund_out(rec),
                "ticket_number": ticket["ticket_number"],
                "message": (f"This refund of {Money.of(amount).display} exceeds the $100 agent limit "
                            f"and has been escalated for human approval (ticket {ticket['ticket_number']})."),
            }

        # Agent-approved refund within policy.
        refund_id = await self.resolutions.insert_refund(
            order_id=order_id, customer_id=v["customer_id"], amount_cents=amount,
            method=method, status="issued", requires_approval=False,
            approved_by_type="ai_agent", policy_id="REF-001", reason=reason,
        )
        rec = await self.resolutions.get_refund(refund_id)
        logger.info("refund_issued", extra={"order_id": order_id, "amount_cents": amount})
        return {
            "status": "issued",
            "refund": self._refund_out(rec),
            "message": (f"Refund of {Money.of(amount).display} to {method.replace('_', ' ')} "
                        f"approved within policy (REF-001)."),
        }

    async def create_return(self, order_id: int, *, reason: str, order_item_ids: list[int]) -> dict:
        rules = {r["order_item_id"]: r for r in await self.orders.return_item_rules(order_id)}
        if not rules:
            raise NotFoundError("Order not found or has no items.", details={"order_id": order_id})
        unknown = [i for i in order_item_ids if i not in rules]
        if unknown:
            raise BusinessRuleError("One or more items do not belong to this order.",
                                    code="invalid_items", details={"unknown_order_item_ids": unknown})
        # Fault & return-shipping payer: store pays when at fault, else customer (RET-004).
        store_fault = reason in ("defective", "damaged", "wrong_item", "missing_item", "not_as_described")
        fault = "store" if store_fault else "customer"
        payer = "store" if store_fault else "customer"
        # Restocking fee only for customer-fault returns, from the highest item rule.
        fee = 0
        if not store_fault:
            for oi in order_item_ids:
                r = rules[oi]
                if r["is_final_sale"] or not r["is_returnable"]:
                    raise BusinessRuleError(
                        f"Item '{r['title']}' is non-returnable ({_NON_RETURNABLE_CLASS_NOTE}).",
                        code="non_returnable", details={"order_item_id": oi},
                    )
                fee += int(r["line_total_cents"] * (r["restocking_fee_pct"] or 0) / 100)
        out = await self.resolutions.insert_return(
            order_id=order_id, customer_id=(await self.orders.get_owner(order_id))["customer_id"],
            reason=reason, fault=fault, return_shipping_payer=payer,
            restocking_fee_cents=fee, order_item_ids=order_item_ids,
        )
        return {
            "return_id": out["return_id"], "rma_number": out["rma_number"], "status": "requested",
            "fault": fault, "return_shipping_payer": payer, "restocking_fee": Money.of(fee),
            "message": (f"Return {out['rma_number']} created. Return shipping paid by {payer}; "
                        f"restocking fee {Money.of(fee).display}. Refund issues after inspection (RET-001)."),
        }

    async def create_claim(self, order_id: int, *, type_: str, order_item_id: int | None,
                           description: str, photos_provided: bool) -> dict:
        owner = await self.orders.get_owner(order_id)
        if not owner:
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        out = await self.resolutions.insert_claim(
            order_id=order_id, order_item_id=order_item_id, customer_id=owner["customer_id"],
            type_=type_, photos_provided=photos_provided, description=description,
        )
        if out["status"] == "awaiting_photos":
            msg = (f"Claim {out['claim_number']} opened. Please provide photos of the issue so we can "
                   f"assess it (DMG-001).")
        else:
            msg = f"Claim {out['claim_number']} opened and is under review (DMG-001)."
        return {**out, "message": msg}

    async def cancel_order(self, order_id: int, *, reason: str, customer_confirmed: bool) -> dict:
        if not customer_confirmed:
            raise BusinessRuleError("Cancellation requires explicit customer confirmation.",
                                    code="confirmation_required")
        elig = await self.cancellation_eligibility(order_id)
        if not elig.eligible:
            raise BusinessRuleError(f"Cannot cancel: {elig.reason}", code="not_cancelable",
                                    details={"status": elig.status, "policy_id": elig.policy_id})
        await self.resolutions.cancel_order(order_id, reason)
        return {"order_number": elig.order_number, "status": "cancelled",
                "message": f"Order {elig.order_number} cancelled. Any authorization will be voided (ORD-002)."}

    async def issue_delay_goodwill(self, order_id: int) -> dict:
        """DELAY-001: suggest + grant a $0/$5/$15 goodwill credit (max one per order)."""
        d = await self.orders.delivery_status(order_id)
        if not d:
            raise NotFoundError("Order not found.", details={"order_id": order_id})
        suggested = int(d.get("suggested_goodwill_credit_cents") or 0)
        already = bool(d.get("goodwill_credit_already_given"))
        if already:
            raise BusinessRuleError("A delay goodwill credit was already granted for this order (DELAY-005).",
                                    code="goodwill_already_given")
        if suggested <= 0:
            raise BusinessRuleError("No delay goodwill credit is warranted (delivered within 2 days of promise).",
                                    code="no_goodwill_warranted",
                                    details={"days_late": d.get("days_late")})
        owner = await self.orders.get_owner(order_id)
        self._credit_id = await self.resolutions.insert_store_credit(
            customer_id=owner["customer_id"], amount_cents=suggested, reason="goodwill_delay",
            source_order_id=order_id, policy_id="DELAY-001",
        )
        return {"order_number": owner["order_number"], "credit": Money.of(suggested),
                "days_late": d.get("days_late"),
                "message": f"Granted a {Money.of(suggested).display} goodwill store credit for the delay (DELAY-001)."}

    # ------------------------------ helpers ------------------------------
    @staticmethod
    def _refund_out(r: dict) -> RefundRecordOut:
        return RefundRecordOut(
            refund_id=r["refund_id"], order_number=r["order_number"],
            amount=Money.of(r["amount_cents"]), method=r["method"], status=r["status"],
            requires_approval=bool(r["requires_approval"]), approved_by_type=r["approved_by_type"],
            policy_id=r["policy_id"], reason=r["reason"], created_at=r["created_at"],
            issued_at=r["issued_at"],
        )
