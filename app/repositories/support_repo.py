"""Support tickets, ticket messages, and the agent-action audit log."""
from __future__ import annotations

from typing import Any

from app.repositories.base import Repository


class SupportRepository(Repository):
    async def _next_id(self, table: str, pk: str) -> int:
        return int(await self.scalar(f"SELECT COALESCE(MAX({pk}), 0) + 1 FROM {table}"))

    # ------------------------------ Tickets ------------------------------
    async def create_ticket(self, *, customer_id: int | None, order_id: int | None,
                            channel: str, category: str | None, subject: str | None,
                            priority: str, escalated: bool, escalation_reason: str | None,
                            assigned_to: str, sentiment: str | None,
                            policy_id_cited: str | None) -> dict:
        tid = await self._next_id("support_tickets", "ticket_id")
        number = f"TKT-{9000 + tid}"
        status = "escalated" if escalated else "open"
        await self.execute(
            """
            INSERT INTO support_tickets(ticket_id, ticket_number, customer_id, order_id, channel,
                 category, subject, status, priority, escalated, escalation_reason,
                 assigned_to, sentiment, policy_id_cited)
            VALUES (:tid, :num, :cid, :oid, :channel, :cat, :subj, :status, :prio,
                    :esc, :esc_reason, :assigned, :sentiment, :pid)
            """,
            {"tid": tid, "num": number, "cid": customer_id, "oid": order_id, "channel": channel,
             "cat": category, "subj": subject, "status": status, "prio": priority,
             "esc": 1 if escalated else 0, "esc_reason": escalation_reason,
             "assigned": assigned_to, "sentiment": sentiment, "pid": policy_id_cited},
        )
        return {"ticket_id": tid, "ticket_number": number, "status": status}

    async def get_ticket(self, ticket_number: str) -> dict | None:
        return await self.fetch_one(
            """
            SELECT ticket_id, ticket_number, customer_id, order_id, category, subject,
                   status, priority, escalated, assigned_to, created_at
            FROM support_tickets WHERE ticket_number = :num
            """,
            {"num": ticket_number},
        )

    async def add_message(self, ticket_id: int, sender: str, body: str) -> int:
        result = await self.execute(
            "INSERT INTO ticket_messages(ticket_id, sender, body) VALUES (:tid, :s, :b)",
            {"tid": ticket_id, "s": sender, "b": body},
        )
        return int(result.lastrowid)

    async def get_messages(self, ticket_id: int) -> list[dict]:
        return await self.fetch_all(
            "SELECT message_id, sender, body, created_at FROM ticket_messages "
            "WHERE ticket_id = :tid ORDER BY created_at, message_id",
            {"tid": ticket_id},
        )

    # --------------------------- Agent actions ---------------------------
    async def record_action(self, *, ticket_id: int, step_number: int, action_type: str,
                            tool_name: str | None, input_json: str | None,
                            output_json: str | None, policy_id: str | None,
                            risk_level: str, requires_approval: bool, status: str,
                            latency_ms: int | None) -> int:
        result = await self.execute(
            """
            INSERT INTO agent_actions(ticket_id, step_number, action_type, tool_name,
                 input_json, output_json, policy_id, risk_level, requires_approval,
                 status, latency_ms)
            VALUES (:tid, :step, :atype, :tool, :inp, :out, :pid, :risk, :req, :status, :lat)
            """,
            {"tid": ticket_id, "step": step_number, "atype": action_type, "tool": tool_name,
             "inp": input_json, "out": output_json, "pid": policy_id, "risk": risk_level,
             "req": 1 if requires_approval else 0, "status": status, "lat": latency_ms},
        )
        return int(result.lastrowid)

    async def create_approval(self, *, ticket_id: int, action_id: int | None, reason: str,
                              amount_cents: int | None) -> int:
        result = await self.execute(
            """
            INSERT INTO approvals(action_id, ticket_id, reason, amount_cents, status)
            VALUES (:aid, :tid, :reason, :amt, 'pending')
            """,
            {"aid": action_id, "tid": ticket_id, "reason": reason, "amt": amount_cents},
        )
        return int(result.lastrowid)
