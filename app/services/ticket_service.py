from __future__ import annotations

from app.core.exceptions import NotFoundError
from app.repositories.orders_repo import OrdersRepository
from app.repositories.support_repo import SupportRepository
from app.schemas.ticket import TicketMessageOut, TicketOut


class TicketService:
    def __init__(self, support: SupportRepository, orders: OrdersRepository) -> None:
        self.support = support
        self.orders = orders

    async def create(self, *, customer_id: int, subject: str, category: str | None,
                     order_number: str | None, message: str, priority: str) -> TicketOut:
        order_id = None
        if order_number:
            o = await self.orders.fetch_one(
                "SELECT order_id, customer_id FROM orders WHERE order_number = :n",
                {"n": order_number},
            )
            if o:
                order_id = o["order_id"]
        created = await self.support.create_ticket(
            customer_id=customer_id, order_id=order_id, channel="chat", category=category,
            subject=subject, priority=priority, escalated=False, escalation_reason=None,
            assigned_to="bot", sentiment=None, policy_id_cited=None,
        )
        await self.support.add_message(created["ticket_id"], "customer", message)
        return await self.get(created["ticket_number"])

    async def get(self, ticket_number: str) -> TicketOut:
        t = await self.support.get_ticket(ticket_number)
        if not t:
            raise NotFoundError("Ticket not found.", details={"ticket_number": ticket_number})
        messages = [
            TicketMessageOut(message_id=m["message_id"], sender=m["sender"],
                             body=m["body"], created_at=m["created_at"])
            for m in await self.support.get_messages(t["ticket_id"])
        ]
        return TicketOut(
            ticket_id=t["ticket_id"], ticket_number=t["ticket_number"],
            customer_id=t["customer_id"], order_id=t["order_id"], category=t["category"],
            subject=t["subject"], status=t["status"], priority=t["priority"],
            escalated=bool(t["escalated"]), assigned_to=t["assigned_to"],
            created_at=t["created_at"], messages=messages,
        )
