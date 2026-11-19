"""Support ticket Tool APIs."""
from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentPrincipal, TicketSvc
from app.core.exceptions import ValidationError
from app.core.security import ensure_owns_customer
from app.schemas.ticket import TicketCreate, TicketOut

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.post("", response_model=TicketOut, status_code=status.HTTP_201_CREATED,
             summary="Create a support ticket")
async def create_ticket(body: TicketCreate, svc: TicketSvc, principal: CurrentPrincipal) -> TicketOut:
    if principal.customer_id is None:
        raise ValidationError("A customer scope (X-Customer-Id) is required to open a ticket.",
                              code="customer_scope_required")
    return await svc.create(
        customer_id=principal.customer_id, subject=body.subject, category=body.category,
        order_number=body.order_number, message=body.message, priority=body.priority,
    )


@router.get("/{ticket_number}", response_model=TicketOut, summary="Retrieve a support ticket")
async def get_ticket(ticket_number: str, svc: TicketSvc, principal: CurrentPrincipal) -> TicketOut:
    ticket = await svc.get(ticket_number)
    if ticket.customer_id is not None:
        ensure_owns_customer(principal, ticket.customer_id)
    return ticket
