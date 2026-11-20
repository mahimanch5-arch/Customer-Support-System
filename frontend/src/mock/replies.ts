import type { MessageMeta } from '../types';

export interface CannedReply {
  content: string;
  meta: MessageMeta;
}

interface Rule {
  test: RegExp;
  reply: CannedReply;
}

/**
 * Stand-in for the agent. Each canned reply mirrors the real contract: prose
 * grounded in a KB article, plus the tool APIs the agent would have called.
 */
const RULES: Rule[] = [
  {
    test: /\b(where|wismo|track|tracking|shipped|shipment|arriv\w*)\b/i,
    reply: {
      content: `Your order **#A-10428** is in transit and on schedule.

- **Carrier:** Dispatch Express · tracking \`DE4471980255\`
- **Last scan:** Nov 18, 06:12 — departed Hyderabad sorting hub
- **Estimated delivery:** Nov 21 (by 8:00 PM)

Nothing is wrong with the shipment, so there is no action for you to take. If it has not arrived by the 21st, come back here and I can open a delay claim for you.`,
      meta: {
        tools: ['GET /orders/{id}/tracking', 'GET /orders/{id}/delivery-estimate'],
        citations: ['_KB/shipping-and-delivery/tracking-a-shipment.md'],
      },
    },
  },
  {
    test: /\b(refund|money back|reimburse\w*)\b/i,
    reply: {
      content: `I checked order **#A-10428** against the refund policy and it **is eligible**.

| Check | Result |
| --- | --- |
| Within 30-day window | Yes — delivered 9 days ago |
| Prior refund on this order | None |
| Payment dispute open | No |
| Amount | $64.00 — under my $100 limit |

I can issue the full **$64.00** back to the Visa ending **4412**, landing in 5–7 business days. Say **"yes, refund it"** and I'll process it.`,
      meta: {
        tools: ['GET /orders/{id}/refund-eligibility', 'GET /orders/{id}/payment'],
        citations: ['_KB/refunds/refund-eligibility-window.md', '_KB/refunds/agent-refund-limits.md'],
      },
    },
  },
  {
    test: /\b(return|exchange|send it back|rma)\b/i,
    reply: {
      content: `Two of the three items on order **#A-10428** can be returned.

1. **Aurora Desk Lamp** — returnable until **Dec 8**. Unused, original packaging.
2. **Cotton Throw Blanket** — returnable until **Dec 8**.
3. **Refill Cartridge (2-pack)** — *not* returnable; consumables are final sale once opened.

Return shipping is free and I'll email you a prepaid label. Which items should I set up?`,
      meta: {
        tools: ['GET /orders/{id}/return-eligibility', 'GET /orders/{id}/items'],
        citations: ['_KB/returns/what-can-be-returned.md', '_KB/product-specific-rules/consumables.md'],
      },
    },
  },
  {
    test: /\b(late|delay\w*|overdue|still not|hasn'?t (arrived|come))\b/i,
    reply: {
      content: `Order **#A-10428** is **4 days late** against its promised date of Nov 15.

Under the delay compensation policy, a 3–6 day delay qualifies for **$5 in store credit**, which I can apply right now — it never expires and stacks with promotions.

Want me to add the $5 credit while we wait on the carrier?`,
      meta: {
        tools: ['GET /orders/{id}/delivery-estimate', 'GET /orders/{id}/status'],
        citations: ['_KB/delays-and-compensation/delay-credit-tiers.md'],
      },
    },
  },
  {
    test: /\b(damaged|broken|cracked|wrong item|defect\w*|missing)\b/i,
    reply: {
      content: `I'm sorry it arrived damaged — that's covered with no return shipment needed.

I've opened claim **CLM-2291** on order **#A-10428**. Your options:

- **Replacement** — ships today, arrives in 2–4 days.
- **Full refund** — $64.00 back to your Visa ending 4412.

Which would you prefer? Photos help us with the carrier but aren't required for you to be made whole.`,
      meta: {
        tools: ['POST /orders/{id}/claims', 'GET /orders/{id}/items'],
        citations: ['_KB/damaged-or-wrong-items/damaged-on-arrival.md'],
      },
    },
  },
  {
    test: /\b(cancel\w*)\b/i,
    reply: {
      content: `Order **#A-10428** has already shipped, so it can no longer be cancelled.

What I *can* do instead:

- **Refuse at the door** — it returns automatically and refunds in full.
- **Accept it, then return it** — I'll pre-issue a free label now.

Shall I prepare the return label so it's waiting in your inbox?`,
      meta: {
        tools: ['GET /orders/{id}/cancellation-eligibility', 'GET /orders/{id}/status'],
        citations: ['_KB/order-management/cancellation-cutoffs.md'],
      },
    },
  },
  {
    test: /\b(human|agent|manager|supervisor|speak to someone|escalat\w*)\b/i,
    reply: {
      content: `Of course — I've escalated this to a human specialist.

**Ticket #SUP-77310** · priority **High** · queue **Billing & Refunds**

You'll get an email reply within **4 business hours**. The full transcript of this conversation is attached, so you won't need to repeat anything.`,
      meta: {
        tools: ['POST /tickets'],
        citations: ['_KB/escalation/when-to-escalate.md'],
        escalated: true,
      },
    },
  },
  {
    test: /\b(credit|promo|coupon|discount|gift card)\b/i,
    reply: {
      content: `Your store credit balance is **$12.50**.

- Applies automatically at checkout, before any promo code.
- **Never expires**, and it stacks with sale pricing and coupons.
- Not transferable, and it can't be cashed out.

Anything else I can check on your account?`,
      meta: {
        tools: ['GET /customers/{id}/store-credit'],
        citations: ['_KB/store-credit-and-promotions/using-store-credit.md'],
      },
    },
  },
];

const FALLBACK: CannedReply = {
  content: `Happy to help with that.

Right now I'm running on **mock data** — the agent layer lands in Phase 3 — so here's what I'd reach for with a question like yours:

- Pull your order and its current status
- Check it against the relevant policy in the knowledge base
- Tell you the verdict, then act only after you confirm

Try asking about **tracking**, a **refund**, a **return**, a **late delivery**, a **damaged item**, or ask for a **human** to see a fuller response.`,
  meta: { citations: ['_KB/README.md'] },
};

export function replyFor(question: string): CannedReply {
  return RULES.find((r) => r.test.test(question))?.reply ?? FALLBACK;
}
