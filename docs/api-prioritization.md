# API Assessment, Prioritization & Consolidation

**Phase:** post-API-build, pre-tool-conversion
**Date:** 2026-11-19
**Scope:** assessment only — no APIs are converted to agent tools in this phase.

---

## 1. Summary

| | Count |
|---|---|
| Business endpoints built (excl. `/health`, `/`) | **27** |
| P1 — convert to tools first | 14 endpoints → **8 tools** |
| P2 — convert in the same phase, lower urgency | 8 endpoints → **4 tools** |
| P3 — backlog, not exposed to the agent | 5 endpoints |
| **Proposed exposed tool count** | **12** (from 27 endpoints, **−56%**) |

The recommendation is **not** to drop functionality. Every P1/P2 capability survives;
20 endpoints collapse into 12 tools by merging reads that the agent almost always
needs together, and by deferring 5 endpoints that no common support query reaches.

> Note on the count: the brief says 26 APIs; the live OpenAPI schema exposes **27**
> business operations (`GET /products` and `GET /products/{id}` are easy to count as
> one). The catalog below is the authoritative list.

### Why tool count matters

Measured from the current OpenAPI schema, a minimal tool definition per endpoint
(name + summary + parameter/body shape) averages **~160 tokens**; all 27 ≈ **4.3k
tokens**. Real tool definitions need "when to use / when not to use" guidance to
keep the model from picking the wrong one, which realistically lands at
250–400 tokens each — so **27 tools ≈ 7–11k tokens on every single LLM call**,
before any conversation or KB content. At 12 tools that is ~3–5k.

The cost is not only tokens. Tool-selection accuracy degrades as near-duplicate
options multiply: an agent facing `get_order`, `get_order_status`, `get_order_items`
and `get_order_invoice` will burn turns choosing among four overlapping reads, and
each wrong pick is another round trip. Fewer, broader tools are both cheaper and
more reliable.

---

## 2. Prioritization criteria

Each endpoint was scored on four axes:

1. **Query frequency** — share of real support contacts that need it. "Where is my
   order" (WISMO) dominates e-commerce support, followed by returns/refunds, then
   cancel/modify, then payments/billing.
2. **Business criticality** — does a resolution path break without it? Refund,
   return, cancel and escalation are the paths that actually close tickets.
3. **Policy coupling** — does it enforce a rule from `_KB/` that the agent must not
   be allowed to improvise (30-day window, one refund per order, $100 agent limit,
   $0/$5/$15 delay tiers, dispute blocks)?
4. **Redundancy** — is the data already returned by another endpoint?

---

## 3. P1 — essential (convert first)

These cover the large majority of inbound customer queries and every path that
resolves a ticket.

| Endpoint | Why P1 |
|---|---|
| `GET /customers/{id}/orders` | The entry point for nearly every conversation: identify which order the customer means. Paginated, filterable by status. |
| `GET /orders/{id}` | Full order detail + items. The single most reused read. |
| `GET /orders/{id}/tracking` | WISMO — the highest-volume query class there is. Carrier, tracking number, event timeline, delivery proof. |
| `GET /orders/{id}/delivery-estimate` | "Is it late?" Supplies `days_late`, which drives the delay-compensation tiers. |
| `GET /orders/{id}/refund-eligibility` | Mandatory gate before any refund talk. Returns the verdict and the policy id. |
| `GET /orders/{id}/return-eligibility` | Per-item return rules (final sale, hygiene, data wipe, bulky, restocking fee). The agent cannot infer these. |
| `GET /orders/{id}/cancellation-eligibility` | Cancel-vs-return branch depends on it. |
| `GET /orders/{id}/refunds` (records) | "Where is my refund?" is a top-5 query and is pure status chasing. |
| `POST /orders/{id}/refunds` | Primary resolution action. Enforces confirmation + the $100 limit + escalation. |
| `POST /orders/{id}/returns` | Primary resolution action (RMA). |
| `POST /orders/{id}/cancel` | Primary resolution action. |
| `POST /orders/{id}/claims` | Damaged / wrong / missing item — a large, distinct contact class with its own flow. |
| `POST /orders/{id}/goodwill-credit` | The only way to honour the delay-compensation policy; capped server-side at one per order. |
| `POST /tickets` | The escalation hatch. Required by the guardrails in `_KB/agent-guardrails.md` — an agent with no way to escalate will improvise instead. |

## 4. P2 — convert, lower urgency

Real but narrower demand, or data the agent needs only in specific branches.

| Endpoint | Why P2 |
|---|---|
| `GET /customers/{id}` | Identity verification, loyalty tier, marketing opt-in. Needed, but much of it can ride along in the session context rather than a tool call. |
| `GET /customers/{id}/store-credit` | Needed when refunding to credit or after goodwill; not needed on most turns. |
| `GET /orders/{id}/payment` | Payment declined, duplicate/pending charges, refund-timing-by-method. ~10% of contacts, and the brand/last4 matter for recognition. |
| `GET /orders/{id}/status` | Correct and cheap, but a strict subset of `GET /orders/{id}`. Keep the endpoint, do not give it a separate tool. |
| `GET /orders/{id}/returns` (records) | Return/RMA status chasing. Lower volume than refund status. |
| `GET /orders/{id}/claims` (records) | Claim status chasing. Same. |
| `GET /tickets/{ticket_number}` | Follow-ups on an escalated ticket. |
| `GET /customers/{id}/addresses` | Address-change queries are common, but there is **no address-write API**, so the read alone cannot resolve them — it can only confirm what is on file before escalating. |

## 5. P3 — backlog (not exposed to the agent)

| Endpoint | Why deferred |
|---|---|
| `GET /orders/{id}/items` | Fully redundant: `OrderDetailOut` already embeds `items`. |
| `GET /orders/{id}/history` | Status-transition audit trail. Useful for human agents and debugging; the customer-facing answer comes from tracking + status. |
| `GET /orders/{id}/invoice` | Low volume, and it is order detail re-shaped with a `bill_to`. Revisit if "send me my invoice" shows up in the logs. |
| `GET /products` (search) | Pre-purchase discovery, not post-purchase support. Exposing search also invites the agent into product recommendation, which is out of scope. |
| `GET /products/{id}` | Product attributes; the order's line items plus `_KB/product-specific-rules/` already cover what support needs. |

Promotion rule: move a P3 endpoint up when logged conversations show the agent
failing or escalating for want of it — demand-driven, not speculative.

---

## 6. Consolidation plan

Five merges take the 20 P1+P2 endpoints down to 12 tool-ready operations. No
endpoint needs deleting — consolidation happens at the **read-aggregation** layer,
so existing clients and tests keep working.

### C1. One order read, with `include` — 8 endpoints → 1

```
GET /orders/{order_id}?include=tracking,payments,history,invoice
```

Absorbs: detail, `status`, `items` (already embedded), `tracking`, `payment`,
`history`, `invoice`, `delivery-estimate`.

Default (no `include`) returns detail + items + the delivery-estimate fields —
enough for the WISMO answer in **one** call instead of three. The order-status and
delivery-lateness fields are small and almost always wanted, so they belong in the
default rather than behind a flag.

### C2. One eligibility call — 3 endpoints → 1

```
GET /orders/{order_id}/resolution-options
```

Absorbs the three `*-eligibility` reads and adds the goodwill-credit verdict.
This is the highest-value merge: when a customer is unhappy the agent needs to
know *all* available levers at once — refund? return? cancel? credit? — and
asking that as three or four separate calls is both slower and invites the agent
to act on the first "eligible" it sees. One verdict object with one policy id per
lever also makes the response auditable.

### C3. One resolution-records call — 3 endpoints → 1

```
GET /orders/{order_id}/resolutions
```

Absorbs the `refunds` / `returns` / `claims` record lists. "What's happening with
my refund/return/claim?" is one customer intent; the customer does not know which
internal object their request became, and neither should the agent have to guess.

### C4. One customer-context call — 3 endpoints → 1

```
GET /customers/{customer_id}?include=addresses,store_credit
```

Absorbs profile, addresses and store-credit balance. `/customers/{id}/orders`
stays separate — it is paginated, filtered and sorted, and merging a list with
different parameters into the profile call would make the tool schema worse, not
better.

### C5. Writes stay 1:1 — deliberately not merged

Refund, return, claim, cancel and goodwill-credit remain five distinct operations.
A single polymorphic `resolve_order(action=…)` tool would save ~600 tokens and is
the wrong trade: each has different required arguments, different confirmation
semantics (a refund needs explicit `customer_confirmed`; a claim needs a
description and photo flag), different approval thresholds, and different audit
records. Collapsing them raises the chance of the model issuing the wrong
irreversible action, which costs far more than the tokens saved.

### Resulting tool surface (12)

| # | Tool | Backed by |
|---|---|---|
| 1 | `find_customer_orders` | `GET /customers/{id}/orders` (+ order-number lookup, see §7) |
| 2 | `get_customer_context` | C4 |
| 3 | `get_order` | C1 |
| 4 | `get_resolution_options` | C2 |
| 5 | `get_order_resolutions` | C3 |
| 6 | `create_refund` | `POST /orders/{id}/refunds` |
| 7 | `create_return` | `POST /orders/{id}/returns` |
| 8 | `create_claim` | `POST /orders/{id}/claims` |
| 9 | `cancel_order` | `POST /orders/{id}/cancel` |
| 10 | `issue_goodwill_credit` | `POST /orders/{id}/goodwill-credit` |
| 11 | `create_ticket` | `POST /tickets` |
| 12 | `get_ticket` | `GET /tickets/{ticket_number}` |

A tighter 9-tool variant is available if token budget is pressing: defer
`get_order_resolutions`, `get_ticket` and `get_customer_context` to a second
iteration, since their intents can be answered (less well) from `get_order` plus
the escalation path. Recommendation is to start at 12 — the three cut tools each
map to a real, frequent intent, and under-tooling shows up as hallucinated status
answers, which is the expensive failure mode.

---

## 7. Gaps found during the assessment

Two things worth fixing before or during the tool-conversion phase.

### G1. No lookup by order number (blocking — recommend P1)

Every order endpoint keys on the internal integer `order_id`
(`app/api/deps.py:80`, `OrdersRepository.get_owner`). Customers only ever quote the
**order number**. The only place `order_number` is resolved today is
`app/services/ticket_service.py:19`, internally.

So the agent's first move must always be "list the customer's orders and
string-match the number myself", which is fragile across pagination and wastes a
call. Fix either way:

- accept `order_number` as a filter on `GET /customers/{id}/orders`, **or**
- let the `{order_id}` path segment resolve either an id or an order number.

The filter is the smaller change and keeps the path parameter typed.

### G2. `customer_confirmed` on returns is a no-op

`ReturnCreate.customer_confirmed` (`app/schemas/resolution.py:120`) is accepted by
the API but never passed to the service — only refund and cancel actually check it
(`app/services/resolution_service.py:150`, `:272`). It defaults to `true`, so the
field is dead weight that reads as a guardrail. Either enforce it for returns too
or remove it, so the tool schema does not advertise a confirmation that is not
checked.

---

## 8. Next phase (not this one)

1. Decide P1/P2 scope and sign off the 12-tool surface.
2. Implement C1–C4 as aggregation endpoints; leave the existing 27 in place.
3. Close G1; resolve G2 either way.
4. Then convert to agent tools, writing each tool's description with explicit
   "use when / do not use when" guidance — that text, not the endpoint count, is
   what determines selection accuracy.
